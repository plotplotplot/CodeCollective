# Create new VM or start existing one
multipass launch 24.04 --name ccportal-vm --mem 4G --cpus 4 --disk 20G || multipass start ccportal-vm