terraform {
  required_version = "~> 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
    util = {
      source  = "poseidon/util"
      version = "~> 0.3.0"
    }
  }
}
