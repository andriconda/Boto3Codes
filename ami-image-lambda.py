import boto3
import collections
import datetime
ec = boto3.client('ec2')

def lambda_handler(event, context):
    reservations = ec.describe_instances(
        Filters=[
            {'Name': 'tag:AMI_Backup', 'Values': ['Yes', 'yes']},
        ]
    ).get(
        'Reservations', []
    )
    instances = sum(
        [
            [i for i in r['Instances']]
            for r in reservations
        ], [])
    print "Found %d instances to create AMI" % len(instances)
    to_tag = collections.defaultdict(list)

    for instance in instances:
        try:
            retention_days = [
                int(t.get('Value')) for t in instance['Tags']
                if t['Key'] == 'AMI_Retention'][0]
        except IndexError:
            retention_days = 7
    for instance in instances:
        _BlockDeviceMappings=[]
        for blk in instance['BlockDeviceMappings']:
            _BlockDeviceMappings.append({
            "DeviceName": blk['DeviceName'],
            "NoDevice": ""
            })
        _BlockDeviceMappings.remove({
            "DeviceName": '/dev/sda1',
            "NoDevice": ""
            })
        response = ec.create_image(
        InstanceId=instance['InstanceId'],
        Name='AMI_'+str(instance['InstanceId'])+'_'+datetime.datetime.now().strftime('%Y-%m-%d_%-H-%M'),
        Description='AMI for '+str(instance['InstanceId']),
        NoReboot=True,
        BlockDeviceMappings=_BlockDeviceMappings
        )
        
        print "Instance-id:%s, Image-id:%s" % (instance['InstanceId'],response['ImageId'])
        to_tag[retention_days].append(response['ImageId'])
        
    for retention_days in to_tag.keys():
        delete_date = datetime.date.today() + datetime.timedelta(days=retention_days)
        delete_fmt = delete_date.strftime('%Y-%m-%d')
        print "Will delete %d AMI on %s" % (len(to_tag[retention_days]), delete_fmt)
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
    account_ids = ['xxxxxxxxxxxxx'] # aws account id to be placed here
    image_response = ec.describe_images(Owners=account_ids, Filters=filters)
    print(image_response)
    for img in image_response['Images']:
        print "Deleting AMI %s" % img['ImageId']
        ec.deregister_image(ImageId=img['ImageId'])
        for bdm in img['BlockDeviceMappings']:
            print "Deleting snapshot %s" % bdm['Ebs']['SnapshotId']
            ec.delete_snapshot(SnapshotId=bdm['Ebs']['SnapshotId'])
