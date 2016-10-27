import boto3
import collections
import datetime
ec = boto3.client('ec2')

def lambda_handler(event, context):

    reservations = ec.describe_instances(
        Filters=[
            {'Name': 'tag:Backup', 'Values': ['Yes', 'yes']},
        ]
    ).get(
        'Reservations', []
    )

    instances = sum(
        [
            [i for i in r['Instances']]
            for r in reservations
        ], [])

    print "Found %d instances that need backing up" % len(instances)

    to_tag = collections.defaultdict(list)

    for instance in instances:
        try:
            retention_days = [
                int(t.get('Value')) for t in instance['Tags']
                if t['Key'] == 'Retention'][0]
        except IndexError:
            retention_days = 7

        for dev in instance['BlockDeviceMappings']:
            if dev.get('Ebs', None) is None:
                continue
            vol_id = dev['Ebs']['VolumeId']
            print "Found EBS volume %s on instance %s" % (
                vol_id, instance['InstanceId'])
            try:
                snap = ec.create_snapshot(
                    VolumeId=vol_id,Description='Snapshot_'+datetime.datetime.now().strftime('%m-%d-%Y')+'_'+str(instance['InstanceId'])
                )
                ec2 = boto3.resource('ec2')
                snapshot=ec2.Snapshot(snap['SnapshotId'])
                snapshot.create_tags(Tags=[
                    {
                        'Key': 'Name',
                        'Value': 'Snapshot_'+vol_id
                        },
                        ])
                print "Instance-id:%s, Volume-id:%s, Snapshot-id:%s" % (instance['InstanceId'],vol_id,snap['SnapshotId'])
                to_tag[retention_days].append(snap['SnapshotId'])
            except Exception as e:
                print("Error occured:",e)
            
            print "Retaining snapshot %s of volume %s from instance %s for %d days" % (
                snap['SnapshotId'],
                vol_id,
                instance['InstanceId'],
                retention_days,
            )
    
    
    for retention_days in to_tag.keys():
        delete_date = datetime.date.today() + datetime.timedelta(days=retention_days)
        delete_fmt = delete_date.strftime('%Y-%m-%d')
        print "Will delete %d snapshots on %s" % (len(to_tag[retention_days]), delete_fmt)
        ec.create_tags(
            Resources=to_tag[retention_days],
            Tags=[
                {'Key': 'DeleteOn', 'Value': delete_fmt},
            ]
        )
    
    delete_on = datetime.date.today().strftime('%Y-%m-%d')
    filters = [
    {'Name': 'tag-key', 'Values': ['DeleteOn']},
    {'Name': 'tag-value', 'Values': [delete_on]},
    ]
    account_ids = ['xxxxxxxxxxxxx'] #AWS account id
    snapshot_response = ec.describe_snapshots(OwnerIds=account_ids, Filters=filters)
    print(snapshot_response)
    for snap in snapshot_response['Snapshots']:
        print "Deleting snapshot %s" % snap['SnapshotId']
        ec.delete_snapshot(SnapshotId=snap['SnapshotId'])
