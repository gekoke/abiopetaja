{ flake-parts
, ...
} @ inputs:
flake-parts.lib.mkFlake { inherit inputs; } {
  systems = [ "x86_64-linux" ];

  imports = [
    ./checks.nix
    ./deploys.nix
    ./dev-shells.nix
    ./nixos-configurations
    ./nixos-modules
    ./overlays.nix
    ./packages.nix
  ];
}
