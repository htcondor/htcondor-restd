#!/usr/bin/make -f
OPENAPI_GENERATOR_VERSION:=4.2.3

echo:=@echo
echotbl:=@printf "%-20s %s\n"

SHELL:=bash

bindings:=java go python
generator_jar:=openapi-generator-cli-$(OPENAPI_GENERATOR_VERSION).jar

.PHONY: help
help:
	$(echo) "Targets:"
	$(echo)
	$(echotbl) "all" "Build all bindings"
	$(echotbl) "help" "This text"
	$(echotbl) "list" "List all targets"
	$(echotbl) "openapi-generator" "Download the openapi-generator-cli JAR"
	$(echo)
	$(echo) "Available bindings:"
	$(echo) "  $(bindings)"
	$(echo)
	$(echo) "Variables:"
	$(echo)
	$(echotbl) "OPENAPI_GENERATOR_VERSION" "The version of openapi-generator"
	$(echotbl) "" "(https://github.com/OpenAPITools/openapi-generator)"
	$(echotbl) "" "to use [$(OPENAPI_GENERATOR_VERSION)]"


.PHONY: all
all: $(bindings)


.PHONY: openapi-generator
openapi-generator: $(generator_jar)


# _not_ .PHONY!
$(generator_jar):
	wget https://repo1.maven.org/maven2/org/openapitools/openapi-generator-cli/$(OPENAPI_GENERATOR_VERSION)/$(generator_jar)


.ONESHELL: $(bindings)
$(bindings): swagger.yaml $(generator_jar)
	if [[ -e .$(@).bak ]]; then
	    rm -rf ".$(@).bak"
	fi
	if [[ -e $(@) ]]; then
	    mv -f "$(@)" ".$(@).bak"
	fi
	generator=$(@)
	if [[ $(@) == go ]]; then
	    generator=go-experimental
	fi
	if java -jar $(generator_jar) generate -g $$generator -o $(@) -i $(<); then
	    rm -rf ".$(@).bak"
	else
	    mv -f ".$(@).bak" "$(@)"
	    false
	fi


# List all the makefile targets
# https://stackoverflow.com/a/26339924
.PHONY: list
list:
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'

