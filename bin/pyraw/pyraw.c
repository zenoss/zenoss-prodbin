/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2011, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


#include <Python.h>

int main(int argc, char **argv) {
  char *program_name = argv[0];
  if (argc < 2) {
    fprintf(stderr, "%s: no python script filename specified\n", program_name);
    exit(EXIT_FAILURE);
  }
  char *args[argc-1];
  int i;
  for (i=1; i<argc; i++) {
    args[i-1] = argv[i];
  }
  Py_Initialize();
  PySys_SetArgv(argc-1, args);
  int socket_status = PyRun_SimpleString(
    "import sys\n"
    "import socket\n"
    "import errno\n"
    "def create_raw_socket(address_family_name, protocol):\n"
    "  try:\n"
    "    address_family = getattr(socket, address_family_name)\n"
    "    return socket.socket(address_family, socket.SOCK_RAW, protocol)\n"
    "  except socket.error, e:\n"
    "    if e.errno == errno.EAFNOSUPPORT:\n"
    "      return None\n"
    "    else:\n"
    "      raise\n"
    "IPV4_SOCKET = create_raw_socket('AF_INET', socket.IPPROTO_ICMP)\n"
    "IPV6_SOCKET = create_raw_socket('AF_INET6', socket.IPPROTO_ICMPV6)\n"
    );
  if (socket_status != 0) {
    Py_Exit(1);
  }
  setuid(getuid());
  char *python_script_filename = args[0];
  FILE *python_script_file_pointer = fopen(python_script_filename, "r");
  if (python_script_file_pointer == NULL) {
    fprintf(stderr, "%s: %s: %s\n", program_name, python_script_filename, strerror(errno));
    exit(EXIT_FAILURE);
  }
  int script_status = PyRun_SimpleFile(python_script_file_pointer, python_script_filename);
  fclose(python_script_file_pointer);
  if (script_status != 0) {
    Py_Exit(EXIT_FAILURE);
  }
  Py_Exit(EXIT_SUCCESS);
}
