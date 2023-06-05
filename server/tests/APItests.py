from clearml.backend_api.session.client import APIClient
from clearml.backend_api.services import tasks
# clearml-task --project my_clear_ml_project 
#--name remote_test_base 
#--repo ssh://git@10.24.65.46:997/Dmitry/baseline_classification.git 
#--branch master 
#--script train_baseliney 
#--queue default
# --docker python:3.10
client = APIClient()

# print(client.projects.get_all())

# script_repo = tasks.Script(
#     repository='ssh://git@10.24.65.46:997/Dmitry/baseline_classification.git'
# )

execution = tasks.Execution(
        queue='default',
        docker_cmd='--image python:3.10'
        # parameters={
        #     "repo": "ssh://git@10.24.65.46:997/Dmitry/baseline_classification.git"
        # }
    )

projects = client.projects.get_all()
queues = client.queues.get_all()

proj_id = None
for i in projects:
    if i.name == 'gitlab_test':
        proj_id = i.id
        break

queue_id = None
for i in queues:
    if i.name == 'default':
        queue_id = i.id
        break

# try:
#     response = client.tasks.create(
#         project=proj_id,
#         name='api_test',
#         type=tasks.TaskTypeEnum.training,
#         execution=execution,
#         script=tasks.Script(
#             repository='ssh://git@10.24.65.46:997/Dmitry/baseline_classification.git',
#             entry_point='train_baseline.py'
#         ),
#     )
# except Exception as e: 
#     print(e)

# print(response.id)

# client.tasks.enqueue(queue=queue_id, task=response.id)

# print(client.queues.get_all(max_task_entries=99999))

# res = client.queues.get_num_entries(queue='5a702b2c6722406fbeb10fd37b471b0d').num
# print(res)

# print(client.tasks.get_all())

# res = client.workers.unregister(worker='alex:gpu1,2')
# print(res)

# res = client.workers.status_report(
#     timestamp=1,
#     worker='alex:gpu1,2'
# )
# import requests

# res = requests.post('http://192.168.143.19:8008/workers.get_all', headers={
#     'Authorization': 'Basic RVlWUTM4NVJXN1kyUVFVSDg4Q1o3RFdJUTFXVUhQOnlmYzhLUW8qR01YYio5cCgocWNZQzdCeUZJcEY3SSY0VkgzQmZVWVhIJW85dlgxWlVaUUVFdzFJbmMpUw=='
# })

# print(res.json())

# res = client.queues.get_all(id=['7b99558a65d14a218976d6e9ee535a43'], only_fields=['entries'])
# res = client.queues.get_next_task(queue='7b99558a65d14a218976d6e9ee535a43')
# print(res)

# res = client.events.get_task_events(task='7595cb373a1a4379a270a319101a3ad0')

# print(res)

# res = client.tasks.get_all(status=[tasks.TaskStatusEnum.completed], id=['51e965a8f6e34331aedc333f3013d757', '7366d13cff414ed7bbfcebfbb4e88465', '6be263c3b98446cbaae12b0a98894db5'])

# res = client.queues.get_all(id=['7b99558a65d14a218976d6e9ee535a43'], only_fields=['entries'])


# res = client.workers.get_all()
# print(res)

# res = client.workers.unregister()
# print(res)

# for entry in res[0].data.entries:
#     print(entry.task)

# res = requests.post('http://192.168.143.19:8008/queues.delete', headers={
#     'Authorization': 'Basic RVlWUTM4NVJXN1kyUVFVSDg4Q1o3RFdJUTFXVUhQOnlmYzhLUW8qR01YYio5cCgocWNZQzdCeUZJcEY3SSY0VkgzQmZVWVhIJW85dlgxWlVaUUVFdzFJbmMpUw=='
# }, json={
#     'queue': 'da0d7ada2d614beabbc401853156b4dc'
# })

# import requests

# res = requests.post('http://0.0.0.0:8008/users.user', headers={
#     'Authorization': 'Basic RVlWUTM4NVJXN1kyUVFVSDg4Q1o3RFdJUTFXVUhQOnlmYzhLUW8qR01YYio5cCgocWNZQzdCeUZJcEY3SSY0VkgzQmZVWVhIJW85dlgxWlVaUUVFdzFJbmMpUw=='
# })

# res.raise_for_status()
# body = res.json()
# print(body)

# for i in range(1, 11):
#     client.queues.create(name=f"Z_DO_NOT_TOUCH_{i}_GPU_QUEUE_FOR_EXECUTION")


# print(dir(tasks.TaskStatusEnum))

# import asyncio
# import random
# import sys
# import os

# sys.path.insert(0, f"{os.path.dirname(__file__)}/../taskmanager")

# print(f"{os.path.dirname(__file__)}/../taskmanager")

# from task import ClearMLTask

# def run_task(task_cfg):
#     task_cfg['gpu_count'] = random.randint(1,10)
#     new_task = ClearMLTask(task_cfg, None, id=0)

#     # process = await asyncio.create_subprocess_shell(task.create_task_command,
#     #                                                         stdout=asyncio.subprocess.PIPE,
#     #                                                         stderr=asyncio.subprocess.PIPE)
    
#     # output, stderr = await process.communicate()
#     # print("stderr:::", stderr)
#     # print("returncode", process.returncode)
    
#     os.system(new_task.create_task_command)

# def main():
#     task_cfg = {}
#     task_cfg["project_name"] = "gitlab_test"
#     task_cfg["experiment_name"] = "gitlab_experiment"
#     task_cfg["branch"] = "master"
#     task_cfg["script"] = "./scripts/AntsBees.py"
#     task_cfg["gpu_count"] = "3"
#     task_cfg["docker_image"] = "python:3.10"
#     task_cfg["additional_script_args"] = ""
#     task_cfg['link'] = "ssh://git@10.24.65.46:997/AlexBaklanov/antsbees_clearml_test.git"

#     for i in range(10):
#         try:
#             run_task(task_cfg)
#         except Exception as e:
#             print("Error:\n", e)


# if __name__ == '__main__':
#     main()

# task_info = client.tasks.get_all(id=['724fa710c32a49e1aaee4e3fee27e97e'])
# # print(task_info[0].data.project)
# print(task_info[0].name)