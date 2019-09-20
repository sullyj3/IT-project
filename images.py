import boto3

s3 = boto3.resource('s3')

def print_buckets():
    for bucket in s3.buckets.all():
        print(bucket.name)

def upload_image(path, s3key):
    with open(path, 'rb') as img:
        bucket = s3.Bucket('shell-safe')
        bucket.put_object(Key=s3key, Body=img)
    print('uploaded!')

print_buckets()
print()
upload_image('cat.png', 'cat.png')
