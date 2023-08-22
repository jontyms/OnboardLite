terraform {
  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
    }
  }
}

provider "openstack" {
    user_name   = "onboard-service"
    tenant_name = "admin"
    password    = "${var.os_password}"
    auth_url    = "https://horizon.hackucf.org:5000/v3.0"
    region      = "hack-ucf-0"
}

resource "openstack_identity_project_v3" "hackucf_member_tenant" {
    name = "${var.tenant_name}"
    description = "Automatically provisioning with Hack@UCF Onboard"
}

resource "openstack_identity_user_v3" "hackucf_member" {
    default_project_id = openstack_identity_project_v3.hackucf_member_tenant.id
    name = "${var.handle}"
    description = "Hack@UCF Dues Paying Member"

    password = "${var.password}"

    ignore_change_password_upon_first_use = false

}

data "openstack_identity_role_v3" "hackucf_member_role" {
    name = "member"
}

resource "openstack_identity_role_assignment_v3" "hackucf_member_role_assignment" {
    user_id = openstack_identity_user_v3.hackucf_member.id
    project_id = openstack_identity_project_v3.hackucf_member_tenant.id
    role_id = data.openstack_identity_role_v3.hackucf_member_role.id
}