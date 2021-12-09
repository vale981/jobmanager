{
  description = "Python job manager for parallel computing.";


  inputs = {
    utils.url = "github:vale981/hiro-flake-utils";
    nixpkgs.url = "nixpkgs/nixos-unstable";
  };

  outputs = { self, utils, nixpkgs, ... }:
    (utils.lib.poetry2nixWrapper nixpkgs {
      name = "jobmanager";
      poetryArgs = {
        projectDir = ./.;
      };
    });
}
