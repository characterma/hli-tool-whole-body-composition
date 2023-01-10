import os
import subprocess
import logging
import json
import argparse
import json
import dpl_client
import getpass

logger = logging.getLogger("register_all")

def register_task(task_path, version, dpl_client):
    """
    Register a dpl task using the version specified in version
    :param task_path: path to the task file.
    :param version: additional version to register task under (used to register tasks in dev that will mimic prod versions)
    :param dpl_client: dpl client object
    :return: None
    """
    print ("TaskPath: {}".format(task_path))
    task = json.load(open(task_path, 'rU'))
    #Now modify version
    task["task"]["version"] = version
    current_image = task["task"]["image"]
    new_image = current_image.replace(":dev", ":{}".format(version))
    task["task"]["image"] = new_image
    task["force"] = True
    output = dpl_client.register_task(task)
    print ("Registering task {}".format(json.dumps(task, indent=4, separators=(',', ': '))))
    print ("Got output: {}".format(json.dumps(output, indent=4, separators=(',', ': '))))


def register_all_tasks(task_dir, version, environment="dev"):
    dpl = dpl_client.DplClient(environment)
    task_files = os.listdir(task_dir)
    if len(task_files) == 0:
        raise Exception("Cannot find task file in {}".format(dir))
    for task_file in task_files:
        task_path = os.path.join(task_dir, task_file)
        register_task(task_path=task_path, version=version, dpl_client=dpl)

def register_pipeline(pipeline_dir, pipeline, environment, version, dpl_client):
    """
    Register a pipeline substituting dev versions for version
    :param pipeline_dir: directory containing pipelines
    :param pipeline: name of the pipeline to register
    :param environment: dpl environment to register in
    :param version: version to replace dev with
    :param dpl_client: dpl client object
    :return: None
    """
    flow = _read_file(os.path.join(pipeline_dir, pipeline, "flow.rb"))
    params = json.loads(_read_file(os.path.join(pipeline_dir, pipeline, 'params.json')))
    steps = json.loads(_read_file(os.path.join(pipeline_dir, pipeline, 'steps.json')))
    for step in range(len(steps["steps"])):
        if steps["steps"][step]["taskVersion"] == "dev":
            steps["steps"][step]["taskVersion"] = version
    print ("Registering pipeline {} with steps: {}".format(pipeline, json.dumps(steps, indent=4, separators=(',', ': '))))

    if environment == "dev":
        pipeline = "{}.{}".format(getpass.getuser(), pipeline)
    dpl_client.register_pipeline(pipeline_id=pipeline, flow=flow, steps=steps, params=params)



def _read_file(path):
    with open(path, 'rU') as input:
        return input.read()



def register_all_pipelines(pipeline_dir, version, environment):
    dpl = dpl_client.DplClient(environment)
    for pipeline in os.listdir(pipeline_dir):
        register_pipeline(pipeline_dir=pipeline_dir, pipeline=pipeline, environment=environment, version=version,
                          dpl_client=dpl)
if __name__ == '__main__':
    """
    Register all tasks and pipelines.  Note this script assumes that it is being run from a Makefile command in the git repos
    base directory.  Also it is assumed that the aws role being used has permissions to register tasks and pipelines
    """
    parser = argparse.ArgumentParser("Script to register pipelines and tasks")
    parser.add_argument("--env", help="dpl environment to register tasks in", default="dev")
    parser.add_argument("--task_dir", help="Directory containing dpl tasks")
    parser.add_argument("--pipeline_dir", help="Directory containing dpl pipelines")
    parser.add_argument("--version", help="Version from the Makefile for registering tasks in dev as they"
                                          "will appear in prod")
    args = parser.parse_args()

    register_all_tasks(args.task_dir, args.version, args.env)
    register_all_pipelines(args.pipeline_dir, args.version, args.env)
