# 
# bati-fusion - Utilitaire de fusion Open Street Map  
# Copyright (c) 2010-2011 JŽr™me Cornet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#---------------------------------------------------------------------
SRCSFILES = tinyxml.cpp \
            tinystr.cpp \
            tinyxmlerror.cpp \
            tinyxmlparser.cpp \
            utils.cpp \
            OSMNode.cpp \
            OSMWay.cpp \
            OSMRelation.cpp \
            OSMRectangle.cpp \
            OSMDocument.cpp \
            main.cpp
#---------------------------------------------------------------------
PROGRAM   = bati-fusion
#---------------------------------------------------------------------
INCLUDESDIR = src
SRCSDIR     = src
DEPSDIR     = .deps
OBJSDIR     = .objs
#---------------------------------------------------------------------

CC = g++
CPPFLAGS = -I$(INCLUDESDIR) -DTIXML_USE_STL
CXXFLAGS = -Wall -O0 -g -ansi -pedantic

LD = $(CC)
LDFLAGS =
LDLIBS = 


SRCS = $(SRCSFILES:%=$(SRCSDIR)/%)

DEPS = $(SRCS:%.cpp=$(DEPSDIR)/%.d)
OBJS = $(SRCS:%.cpp=$(OBJSDIR)/%.o)

all: $(PROGRAM)

.PHONY: clean
clean: 
	-rm -rf $(DEPSDIR) $(OBJSDIR) core $(PROGRAM)

$(PROGRAM):	$(DEPS) $(OBJS)
	$(LD) $(LDFLAGS) $(OBJS) $(LDLIBS) -o $(PROGRAM) 2>&1 | c++filt
               
$(DEPSDIR)/%.d: %.cpp
	@ echo Making dependencies for $<
	@ mkdir -p $@ 2>/dev/null || echo "$@ already exists" >/dev/null
	@ rmdir $@ 2>/dev/null || echo "$@ already exists" >/dev/null
	@ $(CC) -E -c -MM $< -o $@ >/dev/null
	@ cat $@ | sed 's#.*:# $@ :#1' > $@.tmp
	@ mv -f $@.tmp $@

$(OBJSDIR)/%.o: %.cpp $(DEPSDIR)/%.d Makefile
	@ mkdir -p $@ 2>/dev/null || echo "$@ already exists" >/dev/null
	@ rmdir $@ 2>/dev/null || echo "$@ already exists" >/dev/null
	$(CC) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

# Include dependency files
ifneq ($(strip $(DEPS)),)
-include $(DEPS)
endif
