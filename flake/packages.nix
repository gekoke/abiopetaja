{ self, ... }:
{
  perSystem = { pkgs, system, ... }: {
    packages = {
      default = pkgs.poetry2nix.mkPoetryApplication {
        projectDir = ../.;
        python = pkgs.python312;
      };

      dependencyEnv = (pkgs.poetry2nix.mkPoetryApplication {
        projectDir = ../.;
        python = pkgs.python312;
      }).dependencyEnv;

      provisionSecretsScript = pkgs.writeShellScriptBin "activate" ''
        SECRET_KEY_FILE="/etc/DJANGO_SECRET_KEY.txt"

        if [ ! -f "$SECRET_KEY_FILE" ]; then
            PASSWORD=$(${pkgs.pwgen}/bin/pwgen -s 32 1)

            echo "$PASSWORD" > "$SECRET_KEY_FILE"

            echo "Generated a new Django secret key and saved it to $SECRET_KEY_FILE"
        else
            echo "File $SECRET_KEY_FILE already exists."
        fi
      '';

      migrationScript = pkgs.writeShellScriptBin "activate" ''
        ${self.packages.${system}.dependencyEnv}/bin/python -m manage makemigrations
        ${self.packages.${system}.dependencyEnv}/bin/python -m manage migrate
        ${self.packages.${system}.dependencyEnv}/bin/python -m manage collectstatic --no-input
      '';

      postMigrationScript = pkgs.writeShellScriptBin "activate" ''
        systemctl restart abiopetaja
      '';
    };
  };
}
