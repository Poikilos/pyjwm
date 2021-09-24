#!/usr/bin/env python3
import os
import xml
from xml.dom.minidom import Document
from xml.dom.minidom import getDOMImplementation
from xml.dom.minidom import parse, parseString
import copy
import sys

def error(msg):
    sys.stderr.write("{}\n".format(msg))
    sys.stderr.flush()

profile = os.environ['HOME']


__doc__ = """
This program generates a submenu (Menu node with sub Menu nodes
containing Program nodes) using a directory containing .desktop files
that adhere to the XDG standard.
- Comments, including the special XDG execution override shebang, are
  ignored. Only files with the "Exec" property will result in a menu
  item (Program node).

Example:
{me} {HOME}/.local/share/applications {HOME}/.local/share/applications-menu
- The command will overwrite the file \"{HOME}/.local/share/applications-menu
- Then add the following inside of a RootMenu node in ~/.jwmrc:
  <Include>{HOME}/.local/share/applications-menu</Include>

 - If you have no ~/.jwmrc, ensure that Joe's Window Manager
   is installed, then if you haven't created a config yet try:
       if [ ! -f "$HOME/.jwmrc" ]; then
           cp /etc/jwm/system/jwmrc ~/.jwmrc
       else
           echo "INFO: You already have a $HOME/.jwmrc."
       fi
""".format(me=sys.argv[0], HOME=profile)


def usage():
    print(__doc__)


def main():
    rootPath = None
    menuPath = None
    if len(sys.argv) < 3:
        # ^ 1st arg is self, and 2 are required.
        usage()
        error("You must specify a directory and a destination file"
              "to write/overwrite.")
        localShare = os.path.join(profile, ".local", "share")
        rootPath = os.path.join(localShare, "applications")
        menuPath = os.path.join(localShare, "applications-menu")
        if os.path.isdir(rootPath):
            error("")
            error("Defaulting to:")
            error("    rootPath: \"{}\"".format(rootPath))
            error("    menuPath: \"{}\"".format(menuPath))
        else:
            exit()
    else:
        rootPath = sys.argv[1]
        menuPath = sys.argv[2]
    generateJWMMenu(rootPath, menuPath)


def generateJWMMenu(rootPath, menuPath):
    applications = []
    # See <https://docs.python.org/3/library/xml.dom.minidom.html>:
    impl = getDOMImplementation()
    dom = impl.createDocument(None, "some_tag", None)
    # top_element = dom.documentElement
    top_element = dom.createElement("JWM")
    rootMenuE = dom.createElement("Menu")
    rootMenuE.setAttribute("label", "~Applications")
    top_element.appendChild(rootMenuE)

    # text = dom.createTextNode('Some textual content.')
    # top_element.appendChild(text)

    readShortcuts(applications, rootPath)

    categorized = getCategorizedShortcuts(applications)

    error("categorized: {}".format(categorized))

    appendApplications(rootMenuE, categorized, dom)

    with open(menuPath, 'w') as outs:
        top_element.writexml(outs, indent="", addindent="  ", newl="\n")


def getDesktopName(item):
    name = item.get("Name")
    if name is None:
        name = item.get("Name[en_US]")
    return name


def readDesktopFile(path):
    ret = None
    with open(path, 'r') as ins:
        for line in ins:
            if line.startswith("#"):
                continue
            if ret is None:
                if line.strip() != "[Desktop Entry]":
                    error("\"{}\" is not a valid desktop file (The"
                          " first line should be \"[Desktop Entry]\""
                          " but is \"{}\").".format(path, line))
                    return None
                ret = {}
                continue
            signI = line.find('=')
            if signI > -1:
                k = line[:signI].strip()
                v = line[signI+1:].strip()
                ret[k] = v
    return ret


def readShortcuts(theseApplications, parentPath, indent=""):
    parentPath = os.path.realpath(parentPath)
    parentName = os.path.split(parentPath)[-1]
    for sub in os.listdir(parentPath):
        subPath = os.path.join(parentPath, sub)
        if not os.path.isfile(subPath):
            readShortcuts(theseApplications, subPath, indent=indent+" ")
            continue
        if not sub.lower().endswith(".desktop"):
            continue
        if sub.startswith("wine-extension-"):
            continue
        error(indent + "* read {}...".format(sub))
        application = readDesktopFile(subPath)
        if application is None:
            continue
        if parentName == "wine":
            application["Categories"] = "wine"
        theseApplications.append(application)


def getCategorizedShortcuts(applications):
    theseCategories = {}
    for i in range(len(applications)):
        application = applications[i]
        catStr = application.get("Categories")
        name = getDesktopName(application)
        Exec = application.get("Exec")
        if Exec is None:
            continue
        if catStr is None:
            items = theseCategories.get(" ")
            if items is None:
                items = []
                theseCategories[" "] = items
            items.append(application)
            continue
        cats = catStr.split(";")
        for cat0 in cats:
            cat = cat0.strip()
            if len(cat) < 1:
                continue
            items = theseCategories.get(cat)
            if items is None:
                items = []
                theseCategories[cat] = items
            items.append(application)
            # ^ Yes, add it multiple times.
    return theseCategories


def appendApplications(parentMenuE, categorized, dom):
    menus = {}
    for category, items in categorized.items():
        error("  * {}".format(category))
        thisMenuE = None
        if category == " ":
            thisMenuE = parentMenuE
        else:
            thisMenuE = menus.get(category)
            if thisMenuE is None:
                thisMenuE = dom.createElement("Menu")
                thisMenuE.setAttribute("label", category)
                menus[category] = thisMenuE
                parentMenuE.appendChild(thisMenuE)
        for item in items:
            error("  - {}".format(item.get("Exec")))
            Exec = item.get("Exec")
            if Exec is None:
                continue
            Name = getDesktopName(item)
            # subE = parseString('<Program>{}</Program>'.format(Exec))
            # ^ That isn't useful here since it returns a Document.
            subE = dom.createElement("Program")

            ExecText = dom.createTextNode(Exec)
            subE.appendChild(ExecText)
            if Name is not None:
                subE.setAttribute("label", Name)
            Icon = item.get("Icon")
            if Icon is not None:
                subE.setAttribute("icon", Icon)
            thisMenuE.appendChild(subE)


if __name__ == "__main__":
    main()
