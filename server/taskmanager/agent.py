DEFAULT_DOCKER_IMAGE_FOR_AGENT = 'python:3.10'

class ClearMLAgent:
    def __init__(self, gpu_list):
        self.gpu_mount = len(gpu_list)
        self.gpu_list = gpu_list

        self.queue = f"queue_for_gpu_mount_{self.gpu_mount}"

        self.command_to_create = f"clearml-agent daemon --detached --docker {DEFAULT_DOCKER_IMAGE_FOR_AGENT} --gpus {','.join([str(i) for i in gpu_list])} --queue {self.queue}"
        self.command_to_delete = f"{self.command_to_create} --stop"