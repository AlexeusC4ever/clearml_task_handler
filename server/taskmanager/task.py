QUEUE_DEFAULT_PREFIX = 'queue_for_gpu_mount_'


class ClearMLTask:

    def __init__(self, task_cfg, web_socket, id):
        self.id = id
        self.web_socket = web_socket
        self.gpu_mount_requirement = 0 if 'gpu_count' not in task_cfg else int(task_cfg['gpu_count'])
        self.used_gpus = []
        self.create_task_command = f"clearml-task" \
        # --project {project_name} \
        # --name {experiment_name} \
        # --repo {repos_link} \
        # --branch {branch} \
        # --script {script} \
        # --queue {queue_name} \
        # --docker {docker_image}".foramt(
        #     project_name=task_cfg['project_name'],
        #     experiment_name=task_cfg['experiment_name'],
        #     branch=task_cfg['branch'],
        #     script=task_cfg['script'],
        #     repos_link=task_cfg['link'],
        #     queue_name=task_cfg[QUEUE_DEFAULT_PREFIX + self.gpu_mount_requirement],
        #     docker_image=task_cfg['docker_image']
        # )
        
        # print(task_cfg)
        
        self.errorMessage = ''
        self.created_status = True
        self.run_status = False
        self.create_task_command += self.__add_cli_parameter__(task_cfg, "project_name", "project")
        self.create_task_command += self.__add_cli_parameter__(task_cfg, "experiment_name", "name")
        self.create_task_command += self.__add_cli_parameter__(task_cfg, "link", "repo")
        self.create_task_command += self.__add_cli_parameter__(task_cfg, "branch", "branch")
        self.create_task_command += self.__add_cli_parameter__(task_cfg, "script", "script")
        self.create_task_command += self.__add_cli_parameter__(task_cfg, "docker_image", "docker")
        self.create_task_command += ' --queue ' + QUEUE_DEFAULT_PREFIX + str(self.gpu_mount_requirement)

        self.create_task_command += self.__add_cli_parameter__(task_cfg, "requirements_file", "requirements", nessesary=False)
        self.create_task_command += self.__add_cli_parameter__(task_cfg, "additional_script_args", "args", nessesary=False)
        self.create_task_command += self.__add_cli_parameter__(task_cfg, "docker_args", "docker_args", nessesary=False)
        self.create_task_command += self.__add_cli_parameter__(task_cfg, "docker_bash_setup_script", "docker_bash_setup_script", nessesary=False)

        if self.created_status is True:
            self.project = task_cfg['project_name']
            self.name = task_cfg['experiment_name']
            self.repo = task_cfg['link']
            self.branch = task_cfg['branch']
            self.script = task_cfg['script']
            self.docker_image = task_cfg['docker_image']
            self.queue = QUEUE_DEFAULT_PREFIX + str(self.gpu_mount_requirement)
            if 'requirements_file' in task_cfg:
                self.requirements = task_cfg['requirements_file']
            if 'additional_script_args' in task_cfg:
                self.args = task_cfg['additional_script_args']
            if 'docker_args' in task_cfg:
                self.docker_args = task_cfg['docker_args']
            if 'docker_bash_setup_script' in task_cfg:
                self.docker_bash_setup_script = task_cfg['docker_bash_setup_script']
            



    def __add_cli_parameter__(self, task_cfg, parameter, cli_parameter_for_command, nessesary=True):
        print(f'{parameter}:', parameter in task_cfg)

        if parameter in task_cfg:
            if task_cfg[parameter] != '':
                return f" --{cli_parameter_for_command} {task_cfg[parameter]}"
        elif nessesary is True:
            self.created_status = False
            self.errorMessage += f"Could not find parameter {parameter} in config for necessary cli parameter '{cli_parameter_for_command}'\n"
        return ''

    # async def run_task(self):