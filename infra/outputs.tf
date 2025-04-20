output "instance_public_ip" {
  description = "Public IP address of the main EC2 instance"
  value       = aws_instance.main.public_ip
}
