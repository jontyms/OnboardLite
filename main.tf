terraform {
  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
    }
  }
}

provider "openstack" {
    user_name   = "${var.username}"
    tenant_name = "${var.tenant_name}"
    password    = "${var.password}"
    auth_url    = "https://horizon.hackucf.org:5000/v3.0"
    region      = "hack-ucf-0"
}

# Creating networks

resource "openstack_networking_network_v2" "gbm_net" {
    name = "${var.member_username}-${var.gbmname}-gbm-network"
    admin_state_up = "true"
}

resource "openstack_networking_subnet_v2" "gbm_subnet" {
    depends_on = [ openstack_networking_network_v2.gbm_net ]
    name = "${var.member_username}-${var.gbmname}-gbm-subnet"
    network_id = openstack_networking_network_v2.gbm_net.id
    cidr = "10.0.0.0/24"
}

# Router creation

resource "openstack_networking_router_v2" "gbm_router" {
  name = "${var.member_username}-${var.gbmname}-gbm-router"
  external_network_id = "6437c13d-a8de-471f-8097-b62d59d064b3"
}

resource "openstack_networking_router_interface_v2" "gbm_net_int" {
  depends_on = [ openstack_networking_router_v2.gbm_router ]
  router_id = openstack_networking_router_v2.gbm_router.id
  subnet_id = openstack_networking_subnet_v2.gbm_subnet.id
}

resource "openstack_networking_secgroup_v2" "gbm_sec_group" {
  name = "${var.member_username}-${var.gbmname} GBM Security Group"
  description = "Security Group auto generated for the ${var.gbmname} GBM"
}

resource "openstack_networking_secgroup_rule_v2" "gbm_sec_group_rule1" {
  direction = "ingress"
  ethertype = "IPv4"
  protocol = "tcp"
  port_range_min = 1
  port_range_max = 65535
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.gbm_sec_group.id
}

resource "openstack_networking_secgroup_rule_v2" "gbm_sec_group_rule2" {
  direction = "ingress"
  ethertype = "IPv4"
  protocol = "icmp"
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.gbm_sec_group.id
}

resource "openstack_networking_secgroup_rule_v2" "gbm_sec_group_rule3" {
  direction = "ingress"
  ethertype = "IPv4"
  protocol = "udp"
  port_range_min = 1
  port_range_max = 65535
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.gbm_sec_group.id
}

# Allocating floating ips to instances

resource "openstack_networking_floatingip_v2" "gbm_fips" {
  depends_on = [ openstack_networking_router_v2.gbm_router ]
  pool = "External Network"
  subnet_ids = ["31252954-a452-4ab2-a5c7-2e09e0ba6d8b"]
}

# Create instances

resource "openstack_compute_instance_v2" "gbm_server" {
  depends_on = [ openstack_networking_network_v2.gbm_net ]
  name            = "${var.member_username}-${var.gbmname}-gbm-server"  #Instance name
  flavor_id       = "2d4659ed-91bb-4c5a-9143-6af2eef6ebbe"
  security_groups = ["default", "${var.member_username}-${var.gbmname} GBM Security Group"]
  user_data       = "#cloud-config\npassword: ubuntu\nchpasswd: { expire: False }\nssh_pwauth: True"

  block_device {
    uuid                  = "${var.imageid}"
    source_type           = "image"
    volume_size           = 15
    boot_index            = 0
    destination_type      = "volume"
    delete_on_termination = true
  }

  network {
    name = openstack_networking_network_v2.gbm_net.name
    fixed_ip_v4 = "10.0.0.100"
  }


}

# Associate floating ips

resource "openstack_compute_floatingip_associate_v2" "deploy_fips_associate" {
  depends_on = [ openstack_compute_instance_v2.gbm_server ]
  floating_ip = openstack_networking_floatingip_v2.gbm_fips.address
  instance_id = openstack_compute_instance_v2.gbm_server.id
}
