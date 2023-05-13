# import os
# import sys
# import aiohttp
# import asyncio
# import json

# async def main():
#     script_path = os.path.dirname(__file__)
#     with open(script_path + '/../config.json') as config_file:
#         cfg = json.load(config_file)

#     server_addr = f"{cfg['serverhost']}"
#     print("Config server: ", server_addr)
#     task_cfg = {}

#     try:
#         with open(TASK_CFG_PATH) as task_config_file:
#             task_cfg = json.load(task_config_file)
#             task_cfg['link'] = sys.argv[1]
#             print(task_cfg)
#     except:
#         print(f'Could not open cfg file: {TASK_CFG_PATH}')
#         task_cfg["project_name"] = "gitlab_test"
#         task_cfg["experiment_name"] = "gitlab_experiment"
#         task_cfg["branch"] = "master"
#         task_cfg["script"] = "./scripts/AntsBees.py"
#         task_cfg["gpu_count"] = "3"
#         task_cfg["docker_image"] = "python:3.10"
#         task_cfg["additional_script_args"] = ""
#         task_cfg['link'] = sys.argv[1]
#     result = {}
#     async with aiohttp.ClientSession(f'{server_addr}') as session:
#         async with session.post('/post', data=task_cfg) as req:
#             result = await req.json()
#             task_id = -1
#             if result['Status'] is False:
#                 print(result['Message'])
#                 raise SystemExit(3)
#             else:
#                 print(f"Task with ID: {result['id']} has been added to queue and waiting for execution")
#                 task_id = result['id']

#         print("result:", result)
#         async with session.post('/get_run_status', data=result) as req:
#             result = await req.json()
#             print(f"Task with ID: {result['id']} info:")
#             print(result['Message'])

# asyncio.run(main())


import asyncio
import os
import sys
import aiohttp
import json


TASK_CFG_PATH = './clearml/task_config.json'


async def main():
    script_path = os.path.dirname(__file__)
    with open(script_path + '/../config.json') as config_file:    
        URL = json.load(config_file)

    task_cfg = {}

    try:
        with open(TASK_CFG_PATH) as task_config_file:
            task_cfg = json.load(task_config_file)
            task_cfg['link'] = sys.argv[1]
            task_cfg['branch'] = sys.argv[2]
            print(task_cfg)
    except:
        print(f'Could not open cfg file: {TASK_CFG_PATH}')
        task_cfg["project_name"] = "gitlab_test"
        task_cfg["experiment_name"] = "gitlab_experiment"
        task_cfg["branch"] = "master"
        task_cfg["script"] = "./scripts/AntsBees.py"
        task_cfg["gpu_count"] = "3"
        task_cfg["docker_image"] = "python:3.10"
        task_cfg["additional_script_args"] = ""
        task_cfg['link'] = sys.argv[1]


    session = aiohttp.ClientSession()
    async with session.ws_connect(f"{URL['serverhost']}:{URL['port']}/ws") as ws:

        await ws.send_json(task_cfg)
        # await ws.send_str("AAAAA")
        async for msg in ws:
            print('Message received from server:', msg.data)
            # await prompt_and_send(ws)

            if msg.type in (aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR):
                break
            if aiohttp.WSMsgType.TEXT:
                print(msg.data)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())