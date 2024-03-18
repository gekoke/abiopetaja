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

      profilesOrder = [ "provisionSecrets" "migration" "service" ];
      profiles = {
        provisionSecrets = {
          sshUser = "root";
          path = deploy-rs.lib.x86_64-linux.activate.custom self.packages."x86_64-linux".provisionSecretsScript "./bin/activate";
        };
        migration = {
          sshUser = "root";
          path = deploy-rs.lib.x86_64-linux.activate.custom self.packages."x86_64-linux".migrationScript "./bin/activate";
        };
        service = {
          sshUser = "root";
          path = deploy-rs.lib.x86_64-linux.activate.nixos self.nixosConfigurations.main;
        };
      };
    };
  };
}
