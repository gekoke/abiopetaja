_:
{
  perSystem = { pkgs, system, ... }: {
    packages = {
      default = pkgs.poetry2nix.mkPoetryApplication {
        projectDir = ../.;
      };
    };
  };
}
