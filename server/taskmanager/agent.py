import os
import shutil
from pyhocon import ConfigFactory
from pyhocon import HOCONConverter


DEFAULT_DOCKER_IMAGE_FOR_AGENT = 'python:3.10'
DEFAULT_STORAGE_DIR = '/storage_labs/3030/clearml_test_storage'
CFG_DIR = './../configs'
DEFAULT_CONFIG_FILE_PATH = '/home/clearml/clearml.conf'


class ClearMLAgent:
    def __init__(self, gpu_list, task_id, task_name, project_name):
        self.gpu_mount = len(gpu_list)
        self.gpu_list = gpu_list
        self.task_id = task_id
        self.task_name = task_name.replace("Clone Of ", "").replace(" ", "")
        self.project_name = project_name.replace(" ", "")

        # self.queue = f"buf_queue_for_task_{task_id}"
        path_to_cfg_file = self.get_path_for_config_file()
        agent_cfg_path = path_to_cfg_file
        cfg_status = self.get_config(path_to_cfg_file)
        if cfg_status is False:
            print(f"Could not get config file: {path_to_cfg_file}, using default config file instead")
            agent_cfg_path = DEFAULT_CONFIG_FILE_PATH

        self.command_to_create = f"clearml-agent --config-file {agent_cfg_path} execute --id {self.task_id} --docker {DEFAULT_DOCKER_IMAGE_FOR_AGENT} --gpus {','.join([str(i) for i in gpu_list])} > /dev/null &"
        self.command_to_delete = f"{self.command_to_create} --stop"

    def get_path_for_config_file(self):
        # return f"{CFG_DIR}/{self.project_name}/{self.task_name}/{self.task_id}"
        dir_path = f"{CFG_DIR}/{self.project_name}/{self.task_name}"
        
        if os.path.exists(dir_path) is False:
            os.makedirs(dir_path)
        
        return f"{dir_path}/{self.task_id}.conf"

    def get_config(self, path_to_cfg_file):
        status = True
        if os.path.exists(path_to_cfg_file) is False:
            status = self.create_new_config(path_to_cfg_file)
        return status

    def create_new_config(self, path_to_cfg_file):
        try:
            conf = ConfigFactory.parse_file(DEFAULT_CONFIG_FILE_PATH)
            path_to_task_cache = f"{DEFAULT_STORAGE_DIR}/{self.project_name}/{self.task_name}"
            path_to_task_storage = f"{DEFAULT_STORAGE_DIR}/{self.project_name}/{self.task_name}/{self.task_id}"

            docker_pip_cache_path = f"{path_to_task_cache}/pip_cache"
            vcs_cache_path = f"{path_to_task_cache}/vcs_cache"
            venvs_cache_path = f"{path_to_task_cache}/venvs_cache"
            docker_apt_cache_path = f"{path_to_task_cache}/apt_cache"
            venvs_builds_path = f"{path_to_task_storage}/venvs_builds"
            # pip_download_cache = f"{path_to_task_cache}/pip_download_cache"
            default_base_dir_path = path_to_task_storage


            # conf.put('agent.pip_download_cache', pip_download_cache)
            conf.put('agent.docker_pip_cache', docker_pip_cache_path)
            conf.put('agent.vcs_cache.path', vcs_cache_path)
            conf.put('agent.venvs_cache.path', venvs_cache_path)
            conf.put('agent.venvs_dir', venvs_builds_path)
            conf.put('agent.docker_apt_cache', docker_apt_cache_path)
            conf.put('sdk.storage.cache.default_base_dir', default_base_dir_path)

            print(f"Writing config to config file: {path_to_cfg_file}")

            with open(path_to_cfg_file, 'w+') as config_file:
                config_file.write(HOCONConverter().to_hocon(conf))

        except Exception as e:
            print(f"Could not create config file for task:\n{e}")
            return False

        return True

    