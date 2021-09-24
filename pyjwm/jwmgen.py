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
- If you have no ~/.jwmrc, ensure that Joe's Window Manager
  is installed, then if you haven't created a config yet try:
      if [ ! -f "$HOME/.jwmrc" ]; then
          cp /etc/jwm/system/jwmrc ~/.jwmrc
      else
          echo "INFO: You already have a $HOME/.jwmrc."
      fi

Arguments starting with "--" are used as options:
--menu-name x: Set the menu-name to x and it will appear as the caption
               for the menu in JWM.

Example 1:
{me} {HOME}/.local/share/applications {HOME}/.local/share/applications-menu
- The command will overwrite the file \"{HOME}/.local/share/applications-menu
- Then add the following inside of a RootMenu node in ~/.jwmrc:
  <Include>{HOME}/.local/share/applications-menu</Include>

Example 2:
You can also roll multiple directories into one Menu by adding more than
two arguments. The last argument is always the target menu file (not
counting arguments starting with "--").
{me} /usr/share/applications /usr/local/share/applications {HOME}/.local/share/system-applications-menu

""".format(me=sys.argv[0], HOME=profile)


def usage():
    print(__doc__)


def main():
    rootPath = None
    menuPath = None
    rootPaths = None
    settings = {}
    if len(sys.argv) < 3:
        # ^ 1st arg is self, and 2 are required.
        usage()
        error("")
        error("* starting...")
        error("You must specify a directory and a destination file"
              " to write/overwrite otherwise default behavior will"
              " occur.")
        localShare = os.path.join(profile, ".local", "share")
        rootPath = os.path.join(localShare, "applications")
        menuPath = os.path.join(localShare, "applications-menu")
        if os.path.isdir(rootPath):
            error("Defaulting to:")
            error("    rootPath: \"{}\"".format(rootPath))
            error("    menuPath: \"{}\"".format(menuPath))
        else:
            exit()
        rootPaths = [rootPath]
    else:
        paths = []
        optionName = None
        first = True
        for arg in sys.argv:
            if first:
                # Skip self.
                first = False
                continue
            elif optionName is not None:
                settings[optionName] = arg
                error("{}={}".format(optionName, arg))
                optionName = None
            elif arg.startswith("--"):
                optionName = arg[2:]
                error("optionName:{}".format(optionName))
            else:
                paths.append(arg)
        rootPaths = paths[:-1]
        menuPath = paths[-1]
        error("")
        error("* starting...")
        error("    rootPaths: \"{}\"".format(rootPaths))
        error("    menuPath: \"{}\"".format(menuPath))
    if settings.get("menu-name") is None:
        settings["menu-name"] = "Programs"
    generateJWMMenu(rootPaths, menuPath, settings)


def execToName(Exec):
    '''
    Transform a command such as "/usr/bin/python %U" to a program
    name such as "python".
    '''
    Exec = Exec.strip()
    execPath = Exec
    if startsAndEndsWith(execPath, '"'):
        execPath = execPath[1:-1]
    if " " in execPath:
        execPath = Exec.split(" ")[0]
    parts = os.path.split(execPath)
    return parts[1]  # parts[1] is the name even if execPath has no path


def getShortcutName(item):
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
            if len(line.strip()) == 0:
                continue
            if ret is None:
                '''
                if line.strip() != "[Desktop Entry]":
                    error("\"{}\" is not a valid desktop file (The"
                          " first line should be \"[Desktop Entry]\""
                          " but is \"{}\").".format(path, line))
                    error("END {}".format(path))
                    return None
                '''
                if line.strip() == "[Desktop Entry]":
                    ret = {}
                    ret["#shortcutPath"] = path
                    # Don't start reading until the entry is reached.
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
    try:
        for sub in os.listdir(parentPath):
            subPath = os.path.join(parentPath, sub)
            if not os.path.isfile(subPath):
                readShortcuts(theseApplications, subPath,
                              indent=indent+" ")
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
    except FileNotFoundError as ex:
        # error("Error: Could not finish listing \"{}\": {}"
        #       "".format(parentPath, ex))
        # This is probably just a bad symlink such as /var/lib/flatpak/app/net.minetest.Minetest/x86_64/stable/73f448a59aa3768d073aee8f38ca72f5c2c9dc79ff6d38a9b702f5630c6d7f1c/files/share/runtime/locale/be/share/be
        pass


def getCategorizedShortcuts(applications):
    theseCategories = {}
    for i in range(len(applications)):
        application = applications[i]
        catStr = application.get("Categories")
        name = getShortcutName(application)
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


def startsAndEndsWith(haystack, needle):
    if len(haystack) < (2 * len(needle)):
        return False
    if not haystack.startswith(needle):
        return False
    if not haystack.endswith(needle):
        return False
    return True


def appendApplications(parentMenuE, categorized, dom):
    menus = {}
    done = {}
    categories0 = sorted(list(categorized.keys()))
    categories = categories0
    error("* processing applications...")
    if " " in categories0:
        categories.remove(" ")
        categories.append(" ")
        # ^ Show uncategorized items last.
    for category in categories:
        items = categorized[category]
        error("  * {}".format(category))
        thisMenuE = None
        if done.get(category) is None:
            done[category] = []
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
            Exec = item.get("Exec")
            if Exec is None:
                continue
            # if startsAndEndsWith(Exec, '"'):
            #     error("    removing quotes from {}...".format(Exec))
            # while startsAndEndsWith(Exec, '"'):
            #     Exec = Exec[1:-1]
            bads = {"%F", "%f", "%U", "%u", "@@"}
            for bad in bads:
                spaceBad = " {}".format(bad)
                Exec = Exec.replace(spaceBad, "")
                spaceBad = ' "{}"'.format(bad)
                Exec = Exec.replace(spaceBad, "")
            execParts = Exec.split(" ")

            # Remove XDG drag&drop & other placeholders (Examples:
            # /usr/bin/flatpak run --branch=stable --arch=x86_64 --command=/app/bin/lbry-app --file-forwarding io.lbry.lbry-app @@u %U @@
            # /usr/bin/flatpak run --branch=stable --arch=x86_64 --command=geeqie --file-forwarding org.geeqie.Geeqie -r @@ %F @@
            for bad in bads:
                while bad in execParts:
                    # (unknown meaning)
                    execParts.remove(bad)
                    Exec = " ".join(execParts)
                quotedBad = '"{}"'.format(bad)
                while quotedBad in execParts:
                    # (unknown meaning)
                    execParts.remove(quotedBad)
                    Exec = " ".join(execParts)
            item["Exec"] = Exec
            if '"' in Exec:
                error("    #shortcutPath='''{}'''".format(item.get("#shortcutPath")))
                error("    execParts='''{}'''".format(execParts))
                error("    Exec='''{}'''".format(Exec))

            Name = getShortcutName(item)
            if Name is None:
                Name = execToName(Exec)  # Set Name before sorting.
            if Name is not None:
                Name = Name.strip()
                if startsAndEndsWith(Name, '"'):
                    Name = Name[1:-1]
            #if item.get("Name") is None:
            item["Name"] = Name
        items = sorted(items, key=lambda x: x.get("Name"))
        for item in items:
            Exec = item.get("Exec")
            if Exec is None:
                continue
            Name = getShortcutName(item)
            # subE = parseString('<Program>{}</Program>'.format(Exec))
            # ^ That isn't useful here since it returns a Document.
            subE = dom.createElement("Program")
            ExecText = dom.createTextNode(Exec)
            subE.appendChild(ExecText)
            if Name is not None:
                if "flatpak" in Exec:
                    if "flatpak" not in Name.lower():
                        Name += " (flatpak)"
                subE.setAttribute("label", Name)
            Icon = item.get("Icon")
            if Icon is not None:
                subE.setAttribute("icon", Icon)
            if not Exec in done[category]:
                done[category].append(Exec)
                thisMenuE.appendChild(subE)
                if '"' in Exec:
                    error("    + {}".format(item.get("Exec")))
            else:
                if '"' in Exec:
                    error("    - {}".format(item.get("Exec")))


def generateJWMMenu(rootPaths, menuPath, settings):
    '''
    Sequential arguments:
    settings -- Provide a valid dictionary that
                contains settings (all settings are optional except
                you must set "menu-name").
                "menu-name" is the caption for the top-tier JWM menu.
    '''
    applications = []
    # See <https://docs.python.org/3/library/xml.dom.minidom.html>:
    impl = getDOMImplementation()
    dom = impl.createDocument(None, "some_tag", None)
    # top_element = dom.documentElement
    top_element = dom.createElement("JWM")
    rootMenuE = dom.createElement("Menu")
    rootMenuE.setAttribute("label", settings["menu-name"])
    top_element.appendChild(rootMenuE)

    # text = dom.createTextNode('Some textual content.')
    # top_element.appendChild(text)

    for rootPath in rootPaths:
        readShortcuts(applications, rootPath)

    categorized = getCategorizedShortcuts(applications)

    # error("categorized: {}".format(categorized))

    appendApplications(rootMenuE, categorized, dom)

    with open(menuPath, 'w') as outs:
        top_element.writexml(outs, indent="", addindent="  ", newl="\n")
    error("* rootPaths: {}".format(rootPaths))
    error("* menuPath: {}".format(menuPath))
    error("* settings: {}".format(settings))
    error("* Saved \"{}\"".format(menuPath))


if __name__ == "__main__":
    main()
