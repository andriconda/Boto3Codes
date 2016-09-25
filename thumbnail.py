import boto3
import time
import json
from PIL import Image
import os

size=100, 100

def upload_thumbnail_to_S3(filename):
	try:
		client = boto3.client('s3')
		client.upload_file(filename,'thumbnail-andriconda',filename)
		return
	except Exception as e:
		print(e)
		
def create_thumbnail(object_key):
	try:
		im=Image.open(str(object_key))
		im.thumbnail(size,Image.ANTIALIAS)
		print('thumbnail created...')
		outfile=os.path.splitext(object_key)[0]+"_thumb.jpg"
		im.save(outfile,"JPEG")
		print('thumbnail saved...')
		return outfile
	except IOError:
		print "cannot create thumbnail for", object_key


sqs=boto3.resource('sqs')
queue = sqs.create_queue(QueueName='thumbnail_queue', Attributes={'DelaySeconds': '5'})
while 1:
	print('Polling SQS...')
	for message in queue.receive_messages():
		data=json.loads(message.body)
	        bucket_name=data["Records"][0]["s3"]["bucket"]["name"]
        	object_key=data["Records"][0]["s3"]["object"]["key"]
        	s3=boto3.resource('s3')
      		object=s3.Object(bucket_name,object_key)
        	object.download_file(object_key)
		
		thumb_filename=create_thumbnail(object_key)
		if thumb_filename is not None:
			message.delete()
	                print('SQS message deleted...')
			upload_thumbnail_to_S3(thumb_filename)
		os.system('rm '+object_key+' '+thumb_filename)
	time.sleep(20)
