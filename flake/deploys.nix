{ self, inputs, ... }:
let
  deploy-rs = inputs.deploy-rs;
in
{
  flake = {
    deploy.nodes.main = {
      hostname = builtins.readFile ../infra/public_ip;
      sshOpts = [ "-o StrictHostKeyChecking=accept-new" ];
      remoteBuild = false;

      profiles = {
        service = {
          sshUser = "root";
          path = deploy-rs.lib.x86_64-linux.activate.nixos self.nixosConfigurations.ec2;
        };
      };
    };
  };
}
