# import argparse
# import sys
# import yaml
# from toolbox import get_config
#
# __author__ = 'fabio'
#
#
# def main(name="wstunneld"):
#     parser = argparse.ArgumentParser(description='WebSocket tunnel endpoint')
#
#     parser.add_argument("-c", "--config",
#                         metavar="CONF_FILE",
#                         help="path to a configuration file",
#                         default=get_config("wstunneld", "{0}.yml".format(name)))
#     # parser.add_argument("-p", "--pid-file",
#     #                     metavar="PID_FILE",
#     #                     help="path to a pid file")
#     parser.add_argument("command",
#                         help="Command to execute", choices=["start", "stop", "restart", "install", "uninstall"])
#     options = parser.parse_args()
#
#     if not options.config:
#         parser.error("No configuration file found. Try using --config option.")
#         sys.exit(-1)
#
#     with open(options.config, 'rt') as f:
#         conf = yaml.load(f.read())
#
#         # if name=="wstuncltd" or conf["endpoint"] == "client":
#         #     wstund = wstuncltd(conf)
#         # elif name=="wstunsrvd" or conf["endpoint"] == "server":
#         #     wstund = wstunsrvd(conf)
#         # else:
#         #     raise ValueError("Wrong name for endpoint")
#         #
#         # getattr(wstund, options.command)()
#         # sys.exit(0)
