{ self, ... }:
{
  perSystem = { pkgs, system, ... }: {
    packages =
      let
        appDefinition = {
          projectDir = ../.;
          python = pkgs.python312;

          postPatch = ''
            substituteInPlace app/pdf.py \
              --replace-fail 'pdflatex' '${pkgs.texliveBasic}/bin/pdflatex'
          '';

          configurePhase = ''
            python -m django compilemessages
          '';

          checkPhase = ''
            pytest
            ${pkgs.pyright}/bin/pyright
          '';
            
          overrides = pkgs.poetry2nix.overrides.withDefaults (_: prev: {
            # FIXME: remove when https://github.com/NixOS/nixpkgs/pull/306553 is merged
            django-allauth = prev.django-allauth.overridePythonAttrs (_: {
              postBuild = ''
                ${prev.django-allauth.passthru.pythonModule.pythonOnBuildForHost.interpreter} -m django compilemessages
              '';
            });
          });
        };

        build = appDefinition: pkgs.poetry2nix.mkPoetryApplication appDefinition;
      in
      {
        abiopetaja = build appDefinition;

        abiopetaja-dev = build (appDefinition // { groups = [ "dev" ]; });

        default = self.packages.${system}.abiopetaja;
      };
  };
}
