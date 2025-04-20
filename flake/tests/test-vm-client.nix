{ pkgs, ... }:
{
  imports = [ ./test-vm-user.nix ];

  environment.systemPackages = [
    pkgs.curl
    pkgs.wget
  ];
}
