import boto3
import time
import paramiko

# Konfigurasi AWS
aws_region = 'us-east-1'  # Ganti dengan region yang sesuai
ami_id = 'ami-0e2c8caa4b6378d8c'  # Ganti dengan ID AMI (misalnya Ubuntu 20.04)
instance_type = 't2.micro'  # Pilih tipe instance yang sesuai
key_name = 'ORA'  # Ganti dengan nama key pair AWS Anda
security_group = 'sg-0bfa02e88af4a6189'  # Ganti dengan security group yang sesuai
subnet_id = 'subnet-0a0b40983c77acdc1'  # Ganti dengan ID subnet Anda
instance_name = 'Proxy-Residensial-EC2'

# Kredensial Luminati (ganti dengan kredensial Anda)
LUMINATI_USERNAME = 'brd.superproxy.io:33335'
LUMINATI_PASSWORD = 'tz9rox7m97if'
LUMINATI_PORT = '22225'  # Biasanya 22225 untuk Luminati
LUMINATI_ZONE = 'us'  # Ganti dengan zona yang sesuai

# Inisialisasi boto3 client untuk EC2
ec2_client = boto3.client('ec2', region_name=aws_region)

# Membuat EC2 Instance
def create_instance():
    response = ec2_client.run_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        KeyName=key_name,
        SecurityGroupIds=[security_group],
        SubnetId=subnet_id,
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {'Key': 'Name', 'Value': instance_name}
                ]
            }
        ]
    )

    instance_id = response['Instances'][0]['InstanceId']
    print(f"Instance created: {instance_id}")
    return instance_id

# Menunggu instance untuk status 'running'
def wait_for_instance(instance_id):
    print(f"Waiting for instance {instance_id} to be running...")
    ec2_client.get_waiter('instance_running').wait(InstanceIds=[instance_id])
    print(f"Instance {instance_id} is running.")
    return True

# Mendapatkan IP Publik instance
def get_instance_ip(instance_id):
    instance = ec2_client.describe_instances(InstanceIds=[instance_id])
    public_ip = instance['Reservations'][0]['Instances'][0]['PublicIpAddress']
    return public_ip

# SSH untuk mengeksekusi perintah pada instance
def ssh_connect(instance_ip):
    key = paramiko.RSAKey.from_private_key_file(f"{key_name}.pem")
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(instance_ip, username='ec2-user', pkey=key)
    return ssh_client

# Instalasi Squid dan konfigurasi Proxy Luminati di EC2
def install_squid_and_configure_proxy(instance_ip):
    ssh_client = ssh_connect(instance_ip)
    commands = [
        # Update sistem dan instal Squid
        'sudo yum update -y',
        'sudo yum install -y squid',
        
        # Menambahkan konfigurasi untuk Luminati Proxy
        f'echo "cache_peer proxy.luminati.io parent {LUMINATI_PORT} 0 no-query login={LUMINATI_USERNAME}-{LUMINATI_ZONE}:{LUMINATI_PASSWORD}" | sudo tee -a /etc/squid/squid.conf',
        'echo "http_access allow all" | sudo tee -a /etc/squid/squid.conf',
        
        # Restart Squid untuk memuat konfigurasi baru
        'sudo systemctl restart squid'
    ]
    
    for command in commands:
        print(f"Executing: {command}")
        stdin, stdout, stderr = ssh_client.exec_command(command)
        print(stdout.read().decode())
        print(stderr.read().decode())

    ssh_client.close()
    print("Proxy Luminati berhasil dikonfigurasi.")

# Main Function
def main():
    # Step 1: Create EC2 Instance
    instance_id = create_instance()

    # Step 2: Wait until instance is running
    wait_for_instance(instance_id)

    # Step 3: Get Public IP of the instance
    public_ip = get_instance_ip(instance_id)
    print(f"Public IP of the instance: {public_ip}")

    # Step 4: Install Squid Proxy and configure Luminati Proxy
    install_squid_and_configure_proxy(public_ip)

if __name__ == '__main__':
    main()
