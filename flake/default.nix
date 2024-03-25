{ flake-parts
, ...
} @ inputs:
flake-parts.lib.mkFlake { inherit inputs; } {
  systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];

  imports = [
    ./checks.nix
    ./deploys.nix
    ./dev-shells.nix
    ./nixos-configurations
    ./overlays.nix
    ./packages.nix
  ];
}
