#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urlparse import urlparse, parse_qs
from xml.dom.minidom import getDOMImplementation
import xml.etree.ElementTree
import json
from vdsm import libvirtconnection

PORT_NUMBER = 10086


def listdev(queries):
    def _getHostDevOfDom(dom_xml):
        domXML = xml.etree.ElementTree.fromstring(dom_xml)
        uuid = domXML.find("uuid").text
        for device in domXML.find("devices").iter("hostdev"):
            if device.get("type") == "usb":
                address = device.find("source").find("address")
                key = "%s#%s" % (address.get("bus"), address.get("device"))
                yield key, uuid

    def _getDevInfo(dev_xml):
        d = dict()
        devXML = xml.etree.ElementTree.fromstring(dev_xml)
        d["name"] = devXML.find("name").text
        d["parent"] = devXML.find("parent").text

        caps = devXML.find("capability")
        d["bus"] = caps.find("bus").text
        d["device"] = caps.find("device").text

        for e in ("vendor", "product"):
            eXML = caps.find(e)
            if eXML is not None:
                if "id" in eXML.attrib:
                    d[e + "_id"] = eXML.get("id")
                if eXML.text:
                    d[e] = eXML.text

        return d

    used = dict()
    devices = list()

    c = libvirtconnection.get()
    for dom in c.listAllDomains():
        for devid, domid in _getHostDevOfDom(dom.XMLDesc()):
            used[devid] = domid

    for dev in c.listDevices("usb_device"):
        device = _getDevInfo(c.nodeDeviceLookupByName(dev).XMLDesc())
        k = "%s#%s" % (device["bus"], device["device"])
        if k in used:
            device["vm"] = used[k]
        devices.append(device)
        
    return "%s(%s);" % ("AllListed", json.dumps(devices))


def attach(queries, reverse=False, callback="attached"):
    def _getDeviceXML(device_xml):
        devXML = xml.etree.ElementTree.fromstring(device_xml)
        caps = devXML.find("capability")
        bus = caps.find("bus").text
        device = caps.find("device").text

        doc = getDOMImplementation().createDocument(None, "hostdev", None)
        hostdev = doc.documentElement
        hostdev.setAttribute("mode", "subsystem")
        hostdev.setAttribute("type", "usb")

        source = doc.createElement("source")
        hostdev.appendChild(source)

        address = doc.createElement("address")
        address.setAttribute("bus", bus)
        address.setAttribute("device", device)
        source.appendChild(address)

        return doc.toxml()

    vm_id = queries["vmId"][0]
    dev_name = queries["devname"][0]

    c = libvirtconnection.get()
    domain = c.lookupByUUIDString(vm_id)
    device_xml = _getDeviceXML(c.nodeDeviceLookupByName(dev_name).XMLDesc())
    if reverse:
        domain.detachDevice(device_xml)
    else:
        domain.attachDevice(device_xml)
    return "%s(\"%s\", \"%s\");" % (callback, vm_id, dev_name)


def detach(queries):
    """
    Two functions share most of the codes.
    """
    return attach(queries, True, "detached")


class myHandler(BaseHTTPRequestHandler):
    FUNC = {
        "/listdev.js": {"func": listdev},
        "/attach.js": {"func": attach, "required": ["devname", "vmId"]},
        "/detach.js": {"func": detach, "required": ["devname", "vmId"]},
    }

    def check(self):
        if self.parsed_path in self.FUNC:
            return reduce(
                lambda x, y: x and y,
                map(
                    lambda q: q in self.parsed_queries,
                    self.FUNC[self.parsed_path].get("required", [])
                ),
                True
            )
        return False

    def run(self):
        try:
            self.ret = self.FUNC[self.parsed_path]["func"](self.parsed_queries)
            return True
        except:
            return False

    def do_GET(self):
        try:
            p_ret = urlparse(self.path)
            self.parsed_path = p_ret.path
            self.parsed_queries = parse_qs(p_ret.query)
            if self.check() and self.run():
                mimetype = "application/javascript"
                self.send_response(200)
                self.send_header("Content-Type", mimetype)
                self.end_headers()
                self.wfile.write(self.ret)
            else:
                self.send_error(404)
        except IOError:
            self.send_error(404, "File Not Found: %s" % self.path[0])

try:
    server = HTTPServer(("", PORT_NUMBER), myHandler)
    server.serve_forever()

except KeyboardInterrupt:
    print "^C received, shutting down the web server"
    server.socket.close()
