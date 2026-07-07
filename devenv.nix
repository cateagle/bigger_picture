{
  pkgs,
  lib,
  config,
  ...
}:

{
  # To autogenerate a ´.devcontainer.json´ file from the devenv.nix
  devcontainer.enable = true;

  languages.python = {
    version = "3.12";
    enable = true;
    venv.enable = true;
    directory = "./backend";
    manylinux.enable = true;         # for python package dependencies
    uv = {
      enable = true;
      sync = {
        enable = true;
        allGroups = true;             # Install all dependency groups
        # groups = [ "dev" "test" ];  # Or pick specific ones
        # extras = [ "plotting" ];    # Specific extras
        # allExtras = true;           # All extras
      };
    };
  };

  # ── Packages ──────────────────────────────────────────────────────────────
  packages = with pkgs; [
    pkg-config
  ];

  # ── Environment variables ─────────────────────────────────────────────────
  env = {
    PKG_CONFIG_PATH = "${pkgs.openssl.dev}/lib/pkgconfig";
    DEVENV_TUI = "0";
  };

  enterShell = ''
    echo "devenv ready"
  '';
}
