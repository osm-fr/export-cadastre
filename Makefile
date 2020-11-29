
PROJECT_DIR=$(shell pwd)
BIN_DIR=$(PROJECT_DIR)/bin
WORK_DIR=$(PROJECT_DIR)/work
DATA_DIR=$(WORK_DIR)/data
WATER_DIR=$(DATA_DIR)/eau
HIDDEN_DIR=$(WORK_DIR)/hidden
LOG_DIR=$(WORK_DIR)/log
LOCK_DIR=$(WORK_DIR)/lock

WORK_DIRECTORIES = $(DATA_DIR) $(WATER_DIR) $(HIDDEN_DIR) $(LOG_DIR) $(LOCK_DIR)

all:config $(WORK_DIRECTORIES)
	sed 's/^AuthUserFile .*/AuthUserFile $(subst /,\/,$(WATER_DIR))\/.htpasswd/' \
	    htaccess-pour-dossier-eau > $(WATER_DIR)/.htaccess
	install htpasswd-pour-dossier-eau $(WATER_DIR)/.htpasswd
	make -C bin $@
	./bin/maj-dep-massif.sh

$(WORK_DIR):
	if [ -d /data/work/cadastre/ ] ; then \
		mkdir -p /data/work/cadastre/export-cadastre \
		&& \
		ln -s /data/work/cadastre/export-cadastre work ; \
	else \
		mkdir work ; \
	fi

$(WORK_DIRECTORIES): $(WORK_DIR)
	mkdir -p $@
	chgrp www-data $@
	chmod g+rwxs $@

config:
	echo "project_dir=$(PROJECT_DIR)" >  config
	echo "bin_dir=$(BIN_DIR)"         >> config
	echo "work_dir=$(WORK_DIR)"       >> config
	echo "data_dir=$(DATA_DIR)"       >> config
	echo "water_dir=$(WATER_DIR)"     >> config
	echo "hidden_dir=$(HIDDEN_DIR)"   >> config
	echo "log_dir=$(LOG_DIR)"         >> config
	echo "lock_dir=$(LOCK_DIR)"       >> config

clean:
	make -C bin $@

distclean:
	make -C bin $@
	rm -f config
	rm -rf work
