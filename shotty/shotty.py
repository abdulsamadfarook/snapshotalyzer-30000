import boto3
import botocore
import click

session = boto3.Session(profile_name='shotty')
ec2 = session.resource('ec2')

def filter_instances(project):
    instances = []

    if project:
        filters = [{'Name':'tag:Project', 'Values':[project]}]
        instances = ec2.instances.filter(Filters=filters)
    else:
        instances = ec2.instances.all()

    return instances

def has_pending_snapshot(volume):
    snapshots = list(volume.snapshots.all())
    return snapshots and snapshots[0].state == 'pending'


@click.group()
def cli():
    """Shotty manages instances and snapshots"""

@cli.group('snapshots')
def snapshots():
    """ Command for volumes """
@snapshots.command('list')
@click.option('--project', default=None, help='Only snapshots with a project (tag Project:<Name>)')
@click.option('--all', 'list_all', default=False, is_flag=True, help='All snapshots')
def list_snapshots(project, list_all):
    "List snapshots"
    instances = filter_instances(project)

    for i in instances:
        for v in i.volumes.all():
            for s in v.snapshots.all():
                print(','.join((
                s.id,
                v.id,
                i.id,
                s.state,
                s.progress,
                s.start_time.strftime("%c")
            )))

            if s.state == 'completed' and not list_all: break
    return

@cli.group('volumes')
def volumes():
    """ Command for volumes """
@volumes.command('list')
@click.option('--project', default=None, help='Only volumes with a project (tag Project:<Name>)')
def list_volumes(project):
    "List EC2 volumes"
    instances = filter_instances(project)

    for i in instances:
        for v in i.volumes.all():
            print(','.join((
                v.id,
                i.id,
                v.state,
                str(v.size) + "Gib",
                v.encrypted and "Encrypted" or "Not Encrypted"
            )))
    return


@cli.group('instances')
def instances():
    """ Command for instances """

@instances.command('snapshot', help="Create a Snapshot of all volumes")
@click.option('--project', default=None, help='Only instances with a project (tag Project:<Name>)')
def create_snapshot(project):
    "Create Snapshot"
    instances = filter_instances(project)

    for i in instances:
        print("The instance {0} is stopping".format(i.id))
        i.stop()
        i.wait_until_stopped()
        for v in i.volumes.all():
            if has_pending_snapshot(v):
                print("Skipping {0}, snapshot already in progress".format(v.id))
                continue
            print("Creating a snapshot of {0}".format(v.id))
            v.create_snapshot(Description="Created by script")

        print("The instance {0} is starting".format(i.id))
        i.start()
        i.wait_until_running()
    print("The job is done")
    return

@instances.command('list')
@click.option('--project', default=None, help='Only instances with a project (tag Project:<Name>)')
def list_instances(project):
    "List EC2 Instances"
    instances = filter_instances(project)

    for i in instances:
        tags = { t['Key']:t['Value'] for t in i.tags or []}
        print(','.join((
            i.id,
            i.instance_type,
            i.placement['AvailabilityZone'],
            i.state['Name'],
            i.public_dns_name,
            tags.get('Project', '<no project>')
            )))
    return

@instances.command('stop')
@click.option('--project', default=None, help='Only instances with a project (tag Project:<Name>)')
def stop_instances(project):
    """Stop EC2 Instances"""
    instances = filter_instances(project)

    for i in instances:
        print("Stopping {0}....".format(i.id))
        try:
            i.stop()
        except botocore.exceptions.ClientError as e:
            print("Could not stop {0} ".format(i.id) + str(e))
            continue
    return

@instances.command('start')
@click.option('--project', default=None, help='Only instances with a project (tag Project:<Name>)')
def start_instances(project):
    """start EC2 Instances"""
    instances = filter_instances(project)

    for i in instances:
        print("Starting {0}....".format(i.id))
        try:
            i.start()
        except botocore.exceptions.ClientError as e:
            print("Could not start {0} ".format(i.id) + str(e))
            continue
    return

if __name__ == '__main__':
    cli()
