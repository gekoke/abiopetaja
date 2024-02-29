_:
{
  perSystem = { pkgs, system, ... }: {
    packages = {
      default = pkgs.poetry2nix.mkPoetryApplication {
        projectDir = ../.;
        python = pkgs.python312;
      };
    };
  };
}
