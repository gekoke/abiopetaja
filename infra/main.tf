provider "aws" {
  region = "eu-north-1"
}

resource "aws_key_pair" "main" {
  key_name   = "main"
  public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFufX1+gB8lYceIB5K5gAsqz8N2UmUmunSXSe17YDq1E geko@carbon"

  tags = {
    Name = "Main SSH public key for provisioned instances"
  }
}

resource "aws_security_group" "main" {
  name        = "main"
  description = "Security group for EC2 instances"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "main" {
  availability_zone = "eu-north-1a"
  ami               = "ami-031fdfb56a3ff2598"
  instance_type     = "t3.micro"
  key_name          = aws_key_pair.main.key_name
  security_groups   = [aws_security_group.main.name]

  root_block_device {
    volume_size = 30
  }

  tags = {
    Name = "Main Abiopetaja instance"
  }
}

resource "local_file" "public_ip" {
  content  = aws_instance.main.public_ip
  filename = "public_ip"
}
