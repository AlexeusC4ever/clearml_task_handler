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
    task_queue_lock = asyncio.Lock()
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
        for i in range(1, self.system_gpu_count + 1):
            self.queues[i] = {'buffer_queue_id': '', 'execution_queue_id': ''}

        for queue in queue_dict:
            if 'queue_for_gpu_mount_' in queue.name:
                gpu_num_queue = queue.name
                gpu_num_queue = re.sub('queue_for_gpu_mount_', '', gpu_num_queue)
                self.queues[int(gpu_num_queue)]['buffer_queue_id'] = queue.id
            elif 'Z_DO_NOT_TOUCH_' in queue.name and '_GPU_QUEUE_FOR_EXECUTION' in queue.name:
                gpu_num_queue = int(queue.name.replace('Z_DO_NOT_TOUCH_', '').replace('_GPU_QUEUE_FOR_EXECUTION', ''))
                self.queues[int(gpu_num_queue)]['execution_queue_id'] = queue.id

        print(f'found queues: {self.queues}')

    async def get_project_name_of_task_by_task_id(self, task_id):
        project_name = ''
        try:
            task_info = self.client.tasks.get_all(id=[task_id], only_fields=['project'])
            project_name = self.client.projects.get_by_id(project=task_info[0].data.project).name
        except Exception as e:
            print(f"Could not get project name of task by task id:\n{e}")

        return project_name

    async def get_task_name_by_task_id(self, task_id):
        task_name = ''
        try:
            task_info = self.client.tasks.get_all(id=[task_id])
            task_name = task_info[0].name
        except Exception as e:
            print(f"Could not get task name by task id:\n{e}")

        return task_name

    async def create_agent(self, gpu_mount, target_task_id):
        new_agent = None
        try:
            gpu_list_for_agent = self.available_gpus_ids[:gpu_mount]
            print("gpu_list_for_agent:", gpu_list_for_agent)

            target_task_name = await self.get_task_name_by_task_id(target_task_id)
            target_task_project_name = await self.get_project_name_of_task_by_task_id(target_task_id)

            if target_task_name == '' or target_task_project_name == '':
                print("Could not get target_task_name or target_task_project_name")

            new_agent = ClearMLAgent(gpu_list_for_agent, target_task_id, target_task_name, target_task_project_name)

            print(f"Command for creating agent:\n{new_agent.command_to_create}")

            process = await asyncio.create_subprocess_shell(new_agent.command_to_create,
                                                            stdout=asyncio.subprocess.PIPE,
                                                            stderr=asyncio.subprocess.PIPE)
            # output, stderr = await process.communicate()
            # print("stderr:::", stderr)
            self.available_gpus_ids = self.available_gpus_ids[gpu_mount:]
            self.current_gpu_available_count -= gpu_mount
            # print(output)
        except Exception as e:
            print(f"Could not run agent for task:\n{e}")

        return new_agent

    async def destroy_agents(self, gpu_mount):
        for agent_index in range(len(self.agents[gpu_mount]))[::-1]: 
            if self.agents[gpu_mount][agent_index].task_id not in self.task_queues[gpu_mount]:
                agent = self.agents[gpu_mount][agent_index]
                print(f"Target task {agent.task_id} has been complete, agent was destroyed by ClearML")

                self.available_gpus_ids.extend(agent.gpu_list)
                self.current_gpu_available_count += agent.gpu_mount
            
                del self.agents[gpu_mount][agent_index]
        

    async def get_project_name_by_id(self, project_name):
        projects = self.client.projects.get_all()
        for project in projects:
            if project.name == project_name:
                return project.id

    async def get_tasks_from_queue(self, queue_id):
        try:
            res = self.client.queues.get_all(id=[queue_id], only_fields=['entries'])
            tasks_list = [entry.task for entry in res[0].data.entries]
        except:
            print(f"Could not get task from queue with id {queue_id}")
            return []
        return tasks_list

    async def get_last_task_id_from_queue(self, queue_gpu_amount):
        tasks_list = await self.get_tasks_from_queue(self.queues[queue_gpu_amount]['buffer_queue_id'])
        task_id = None
        if len(tasks_list) == 0:
            print(f"tasks_list is empty!!! queue: {queue_gpu_amount}:{self.queues[queue_gpu_amount]}")
            return task_id
        else:
            try:
                task_id = tasks_list[-1]
                print("New task id:", task_id)
                self.task_queues[queue_gpu_amount].append(tasks_list[-1])
            except Exception as e:
                print(f"Could not add task to task queue {queue_gpu_amount}\n", e)
                return None
            return task_id

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

        return output

    async def check_tasks_for_completion(self, gpu_mount_queue):
        if len(self.task_queues[gpu_mount_queue]) == 0:
            return 0

        print("QUEUES:", [i for i in self.task_queues[gpu_mount_queue]])
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

    async def log_launched_task(self, task_id):
        # with open('launched_tasks.txt', 'r+') as f:
        #     # ...
        #     f.seek(0, 2)       # перемещение курсора в конец файла
        #     f.write(task_id)  # собственно, запись
        pass

    async def tasks_status_check(self, web_app):
        buffer_queues_to_delete = []

        while(True):
            # conf = self.client.queues.get_all()
            await self.check_queues_for_cloned_tasks()
            print('SERVER TASK QUEUE:', self.task_queue)
            print('DICT OF GPU QUEUES TASKS:', self.task_queues)
            print('RUNNING AGENTS:', self.agents)
            print('AMOUNT OF AVAILABLE GPUS:', self.current_gpu_available_count)
            if len(self.task_queue) > 0:
                # async with task_queue_lock:
                try:
                    tasks_to_delete = []
                    async with self.task_queue_lock:
                        for task_idx in range(len(self.task_queue))[::-1]:
                            if self.current_gpu_available_count == 0:
                                break
                            
                            task = self.task_queue[task_idx]

                            if task.gpu_mount_requirement > self.current_gpu_available_count:
                                # continue
                                break

                            if task.created_from_cli is False:
                                print("Handling external task request")

                                new_agent = await self.create_agent(task.gpu_mount_requirement, task.id)

                                if new_agent:
                                    self.agents[task.gpu_mount_requirement].append(new_agent)
                                    print("Succesfully created agent for task")
                                    # await self.log_launched_task(task.id)
                                    # await self.delete_buffer_queues(buf_queue_id)


                                tasks_to_delete.append(task_idx)
                                continue
                            else:
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
                            print(f"delete task with idx: {task_idx} from server queue")
                            del self.task_queue[task_idx]

                except Exception as e:
                    print(f"Error handling tasks:\n{e}")

            try:
                async with self.agent_lock:
                    # print(f"agents: {self.agents}")
                    for queue_gpu_mount, queue_id in self.queues.items():
                        await self.check_tasks_for_completion(queue_gpu_mount)
                        await self.destroy_agents(queue_gpu_mount)
                            

            except Exception as e:
                print("Error while deleting agents:\n", e)

            await asyncio.sleep(CHECK_QUEUES_DELAY_IN_SECONDS)

    #this method checks queues for tasks that wasn't gotten from client
    #such tasks can be obtained by cloning tasks right on server or from user by his hands
    async def check_queues_for_cloned_tasks(self):
        async with self.task_queue_lock:
            for queue_gpu_mount, queue_id in self.queues.items():
                tasks_list = await self.get_tasks_from_queue(queue_id['buffer_queue_id'])
                for task in tasks_list:
                    if task not in self.task_queues[queue_gpu_mount]:
                        print(f"Add task from external request, id of task {task}")
                        task_cfg = {}
                        task_cfg['gpu_count'] = queue_gpu_mount
                        task_cfg['task_id'] = task
                        self.task_queue.insert(0, ClearMLTask(id=self.CURRENT_ID, web_socket=None, task_cfg=task_cfg, created_from_cli=False))
                        self.task_queues[queue_gpu_mount].append(task)
                #  = list(set(self.task_queues[queue_gpu_mount]).union(set(tasks_list)))


    async def add_task_to_queue(self, task_cfg, web_socket):
        new_task = ClearMLTask(task_cfg, web_socket, self.CURRENT_ID)
        print("FINAL COMMAND: ", new_task.create_task_command)
        if new_task.created_status is False:
            new_task.errorMessage += '\nCould not add task to queue'
        else:       
            async with self.task_queue_lock:
                self.task_queue.insert(0, new_task)
                self.CURRENT_ID += 1
                print("Adding task to dict", self.task_queue)

        return new_task

if __name__ == '__main__':
    tm = TaskManager()
