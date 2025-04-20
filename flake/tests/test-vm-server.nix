{ self, pkgs, ... }:
{
  imports = [
    ./test-vm-user.nix
    self.nixosModules.abiopetaja
  ];

  system.stateVersion = "24.05";

  environment.systemPackages = [ pkgs.curl ];

  services.abiopetaja = {
    enable = true;
    provisionCertificates = false;
    domains = [ "server" ];
  };
}
