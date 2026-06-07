# Root passthrough to the $0 local-OSS dev substrate in local/.
# Additive, local-only, no cloud, no credentials. Application code unchanged.

.PHONY: up down smoke seed logs ps rebuild

up down smoke seed logs ps rebuild:
	$(MAKE) -C local $@
