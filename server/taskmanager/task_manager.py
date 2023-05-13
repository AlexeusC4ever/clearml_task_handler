import os
import re
import torch
import aiohttp
import asyncio
from subprocess import Popen
from .task import ClearMLTask
from .agent import ClearMLAgent
from clearml.backend_api.session.client import APIClient
from clearml.backend_api.services import tasks

CHECK_QUEUES_DELAY_IN_SECONDS = 5



class TaskManager:
    task_queues = None
    available_gpus_ids = []
    # autorization_token = 
    system_gpu_count = 0
    current_gpu_available_count = 0
    CURRENT_ID = 0
    task_dict_lock = asyncio.Lock()
    agent_lock = asyncio.Lock()

    def __init__(self):
        self.system_gpu_count = torch.cuda.device_count()
        self.task_queues = {queue_gpu_amount: [] for queue_gpu_amount in range(self.system_gpu_count + 1)}
        self.task_queue = []
        self.agents = {queue_gpu_amount: [] for queue_gpu_amount in range(self.system_gpu_count + 1)}
        # task_dict = {}
        self.current_gpu_available_count = int(self.system_gpu_count)
        self.available_gpus_ids = [i for i in range(self.system_gpu_count)]
        self.client = APIClient()

        queue_dict = self.client.queues.get_all()

        self.queues = {}

        for queue in queue_dict:
            if 'queue_for_gpu_mount_' in queue.name:
                gpu_num_queue = queue.name
                gpu_num_queue = re.sub('queue_for_gpu_mount_', '', gpu_num_queue)
                self.queues[int(gpu_num_queue)] = queue.id

    async def create_agent(self, gpu_mount):
        new_agent = None
        try:
            gpu_list_for_agent = self.available_gpus_ids[:gpu_mount]
            print("gpu_list_for_agent:", gpu_list_for_agent)
            new_agent = ClearMLAgent(gpu_list_for_agent)

            process = await asyncio.create_subprocess_shell(new_agent.command_to_create,
                                                            stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.PIPE)
            output, stderr = await process.communicate()
            print("stderr:::", stderr)
            self.available_gpus_ids = self.available_gpus_ids[gpu_mount:]
            self.current_gpu_available_count -= gpu_mount
        except Exception as e:
            print(f"Could not run agent for task:\n{e}")
            
        print(output)

        return new_agent

    async def destroy_agents(self, gpu_mount):
        for agent_index in range(len(self.agents[gpu_mount]))[::-1]: 
            agent = self.agents[gpu_mount][agent_index]
            process = await asyncio.create_subprocess_shell(agent.command_to_delete,
                                                            stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.PIPE)
            output, stderr = await process.communicate()
            if process.returncode != 0:
                print("error while deleting agent")
            self.available_gpus_ids.extend(agent.gpu_list)
            self.current_gpu_available_count += agent.gpu_mount
        
            del self.agents[gpu_mount][agent_index]
        

    async def get_project_name_by_id(self, project_name):
        projects = self.client.projects.get_all()
        for project in projects:
            if project.name == project_name:
                return project.id

    async def get_last_task_id_from_queue(self, queue_gpu_amount):
        tasks_list = self.client.queues.get_all(id=[self.queues[queue_gpu_amount]], only_fields=['entries'])
        if len(tasks_list) == 0:
            print(f"tasks_list is empty!!! queue: {queue_gpu_amount}:{self.queues[queue_gpu_amount]}")
            return False
        else:
            try:
                task_id = tasks_list[0].data.entries[-1].task
                print("New task id:", task_id)
                self.task_queues[queue_gpu_amount].append(tasks_list[-1].data.entries[-1].task)
            except Exception as e:
                print("PIZDEC KAKOY TO NAHUY SUKA BLYAT!!!\n", e)
                return False
            return True

    async def run_task(self, task):
        # os.system(task.create_task_command)
        if task.run_status is True:
            return
        status = True
        try:
            process = await asyncio.create_subprocess_shell(task.create_task_command,
                                                            stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.PIPE)
            output, stderr = await process.communicate()
            print("stderr:::", stderr)
            print("returncode", process.returncode)
            #there are also proc.returncode
        except Exception as e:
            status = False
            print(e)

        gpu_mount = int(task.gpu_mount_requirement)

        if process.returncode == 0:
            print("Trying to  get id of new task")
            if await self.get_last_task_id_from_queue(gpu_mount) is False:
                print("Could not get id of new task")
                return output
            try:
                async with self.agent_lock:
                    if status is True:
                        print(f"creating agent for {gpu_mount} gpus")
                        new_agent = await self.create_agent(gpu_mount)
                        if new_agent:
                            self.agents[gpu_mount].append(new_agent)
                        else:
                            print('Could not create an agent for task')
                            task.web_socket.send_str('Could not create an agent for task')
            except Exception as e:
                print("Run agent error:\n", e)

        return output

    async def check_tasks_for_completion(self, gpu_mount_queue):
        if len(self.task_queues[gpu_mount_queue]) == 0:
            return 0
        # queue_id = self.queues[gpu_mount_queue]
        # for task in self.task_queues[gpu_mount_queue]:
        completed_tasks = self.client.tasks.get_all(status=[tasks.TaskStatusEnum.completed,
                                                       tasks.TaskStatusEnum.stopped,
                                                       tasks.TaskStatusEnum.closed,
                                                       tasks.TaskStatusEnum.failed,
                                                    #    tasks.TaskStatusEnum.published
                                                       ],
                                                id=[i for i in self.task_queues[gpu_mount_queue]])

        completed_tasks_ids = [i.id for i in completed_tasks]

        self.task_queues[gpu_mount_queue] = list(set(self.task_queues[gpu_mount_queue]) - set(completed_tasks_ids))
        return len(self.task_queues[gpu_mount_queue])

    async def tasks_status_check(self, web_app):
        while(True):
            # conf = self.client.queues.get_all()
            # print('DICT OF TASKS:', self.task_queue)
            if len(self.task_queue) > 0:
                # async with task_queue_lock:
                try:
                    tasks_to_delete = []
                    for task_idx in range(len(self.task_queue))[::-1]:
                        if self.current_gpu_available_count == 0:
                            break
                        
                        task = self.task_queue[task_idx]

                        if task.gpu_mount_requirement > self.current_gpu_available_count:
                            # continue
                            break

                        shell_output = await self.run_task(task)

                        try:
                            await task.web_socket.send_str(shell_output.decode())
                            await task.web_socket.close()
                            # del self.task_queue[task.id]
                            tasks_to_delete.append(task_idx)
                        except Exception as e:
                            print("BLYAT", e)
                            # if str(task_key) in self.task_queue:
                            #     # task.web_socket.close()
                            #     # del self.task_queue[task.id]
                            tasks_to_delete.append(task_idx)
                
                    for task_idx in tasks_to_delete:
                        print(f"delete task with idx: {task_idx}")
                        del self.task_queue[task_idx]

                except Exception as e:
                    print(f"Error handling tasks:\n{e}")

            try:
                async with self.agent_lock:
                    # print(f"agents: {self.agents}")
                    for queue_gpu_mount, queue_id in self.queues.items():
                        task_mount_in_queue = await self.check_tasks_for_completion(queue_gpu_mount)

                        # task_mount_in_queue = self.client.queues.get_num_entries(queue_id).num
                        # print(f"queue: {queue_gpu_mount}, contains {task_mount_in_queue} tasks")
                        
                        if task_mount_in_queue == 0 and len(self.agents[queue_gpu_mount]) > 0:
                            print(f"destroying agents for {queue_gpu_mount} gpus queue")
                            await self.destroy_agents(queue_gpu_mount)
                            

            except Exception as e:
                print("Error while delleting agents:\n", e)


            await asyncio.sleep(CHECK_QUEUES_DELAY_IN_SECONDS)

    async def add_task_to_queue(self, task_cfg, web_socket):
        # if 'gpu_count' not in task_cfg:
        #     gpu_count = 0
        # else:
        #     gpu_count = task_cfg['gpu_count']

        # self.task_queues[gpu_mount].append(ClearMLTask(task_cfg))
        new_task = ClearMLTask(task_cfg, web_socket, self.CURRENT_ID)
        # self.task_queues.append(new_task)
        print("FINAL COMMAND: ", new_task.create_task_command)
        if new_task.created_status is False:
            new_task.errorMessage += '\nCould not add task to queue'
        else:       
            # async with task_queue_lock:
            self.task_queue.append(new_task)
            self.CURRENT_ID += 1
            print("Adding task to dict", self.task_queue)

        return new_task

if __name__ == '__main__':
    tm = TaskManager()
    # print(tm.task_queues)
    # await tm.tasks_status_check()
