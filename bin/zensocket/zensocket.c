/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2007, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


#include <sys/types.h>

#include <getopt.h>
#if defined (__SVR4) && defined (__sun)
/* ifaddrs.h doesn't exist on Sun */
#else
#   include <ifaddrs.h>
#endif
#include <netdb.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

#include <sys/socket.h>

#include <netinet/in.h>

#define MIN(a,b) ((a) < (b) ? (a) : (b))


static struct option options[] = {
    {"ping",   no_argument, 0, 0},
    {"listen", no_argument, 0, 0},
    {"proto", required_argument, 0, 0},
    {"port", required_argument, 0, 0},
    {"socketOpt", required_argument, 0, 0},
    { 0, 0, 0, 0 }
};

#define ZEN_MAX_SO_OPTIONS 32
struct socket_options_set {
  int code;
  int value;
};

static void error(const char * fmt, ...) {
    va_list args;

    fprintf(stderr, "ZenSocket Error: ");
    va_start(args, fmt);
    vfprintf(stderr, fmt, args);
    va_end(args);
    fprintf(stderr, "\n");
    exit(EXIT_FAILURE);
}

static void usage(const char *name) {
  printf("\n");
  printf("Usage: %s [options] -- command to run\n", name);
  printf("\n");
  printf("Send Options:\n");
  printf("  --ping                       send ICMP packets\n");
  printf("\n");
  printf("Listen Options:\n");
  printf("  --listen                     listen for incoming packets\n");
  printf("  --port:[interface:]number    the numerical port to listen on\n");
  printf("  --proto:[udp|tcp]            protocol to listen for\n");
  printf("\n");
  printf("Other Options:\n");
  printf("  --socketOpt=option:value     set the socket option\n");
  printf("      *NOTE*: socket options are numerical values from sys/socket.h\n");
  printf("\n");
  exit(EXIT_FAILURE);
}

static in_addr_t getAddress(const char *interface) {
  int a, b, c, d;

  if (!interface || !*interface) {
    return INADDR_ANY;
  }

  if (sscanf(interface, "%d.%d.%d.%d", &a, &b, &c, &d) != 4) {
    struct addrinfo *res = 0, *p;

    if (getaddrinfo(interface, NULL, NULL, &res) == 0) {
	    in_addr_t result;
	    for (p = res; p; p = p->ai_next) {
        if (p->ai_family == AF_INET) {
          struct sockaddr_in * in = (struct sockaddr_in *)p->ai_addr;
          result = in->sin_addr.s_addr;
          break;
        }
	    }

	    freeaddrinfo(res);
	    if (p) {
        return result;
      }
    }

    fprintf(stderr, "Warning: unable to decode address %s\n", interface);
    return INADDR_ANY;
  }

  return htonl( ((a & 0xff) << 24) | ((b & 0xff) << 16) | 
                ((c & 0xff) << 8)  |  (d & 0xff) );
}

/*
 * Create an IPv6 socket and bind it to the listen port.
 */
static int bind_ipv6_socket(int type, uint16_t port, int *ipv6_socket) {
  int sock;
  int v6only_value;
  int v6only_status;
  struct sockaddr_in6 address;
  sock = socket(PF_INET6, type, 0);
  if (sock == -1) {
    return -1;
  }
  v6only_value = 0;
  v6only_status = setsockopt(sock, IPPROTO_IPV6, IPV6_V6ONLY, &v6only_value, sizeof(v6only_value));
  if (v6only_status == -1) {
    close(sock);
    return -1;
  }
  address.sin6_family = AF_INET6;
  address.sin6_port = htons(port);
  address.sin6_addr = in6addr_any;
  if (bind(sock, (struct sockaddr *) &address, sizeof(struct sockaddr_in6)) < 0) {
    close(sock);
    return -1;
  }
  *ipv6_socket = sock;
  return 0;
}

int main(int argc, char **argv) {
  char **args = 0;
  const char * replace = "$privilegedSocket";
  int i, c;
  int ping = 0;
  int listen = 0;
  char * proto = NULL;
  int proto_sock = SOCK_DGRAM;
  const char * interface = 0;
  unsigned short port = 0;
  int sock = -1;
  char filenoString[10] = "";
  int so_index = -1; /* Track number of options set */
  int max_index = -1;
  struct socket_options_set so_setting[ZEN_MAX_SO_OPTIONS];
  int bind_ipv6_status;
  
  if (geteuid() != 0) {
    error("zensocket needs to be run as root or setuid");
  }

  if (argc < 2) {
    usage("zensocket");
  }

  
  while (1) {
    int option_index = 0;
    int c = getopt_long(argc, argv, "", options, &option_index);
    if (c == -1)
	    break;
    switch (c) {
    case 0:
      /* ping option */
	    if (option_index == 0)
        ping = 1;

      /* listen option */
	    if (option_index == 1) {
        listen = 1;
      }

      /* protocol option */
      if (option_index == 2) {
        if (!strcmp(optarg, "tcp")) {
          proto_sock = SOCK_STREAM;
        }
        else if (!strcmp(optarg, "udp")) {
          proto_sock = SOCK_DGRAM;
        }
        else {
          error("proto should be either tcp or udp");
        }
        proto = optarg;
      }

      /* port option */
      if (option_index == 3) {
        char * portString = optarg;
        char * colon = strchr(optarg, ':');
        if (colon) {
          *colon = '\0';
          interface = optarg;
          portString = colon + 1;
        }
   
        port = atol(portString);
        if (port == 0) {
          error("Unable to use port number");
        }
	    }

      /* socket option */
      if (option_index == 4) {
        char * socketString = optarg;
        char * colon = strchr(optarg, ':');
        char * optValue = NULL;
        if (colon) {
          *colon = '\0';
          optValue = colon + 1;
        } else {
          error("Socket option needs to be of the form #:#");
        }

        so_index++;
        if(so_index >= ZEN_MAX_SO_OPTIONS) {
          error("Too many socket options specified");
        }
        so_setting[so_index].code = atol(socketString);
        so_setting[so_index].value = atol(optValue);
      }
	    break;

    default:
	    usage(argv[0]);
    }
  }

  /* --ping and --listen are mutually exclusive - one must be specified */
  if (ping == listen) {
    usage(argv[0]);
  }

  if (ping) {
    sock = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
    if (sock < 0)
	    error("Unable to create ping socket");
  }
  else if (listen) {
    
    if (interface && strcmp(interface, "ipv6") == 0) {
    
      bind_ipv6_status = bind_ipv6_socket(proto_sock, port, &sock);
      if (bind_ipv6_status) {
        error("Failed to bind IPv6 socket: %s", strerror(errno));
      }
    
    } else {
      
      int reuse_addr = 1;
      struct sockaddr_in addr;
      int so_option, so_value;

      sock = socket(AF_INET, proto_sock, 0);
      if (sock < 0) {
        error("Unable to create listen socket");
      }

      memset(&addr, 0, sizeof(addr));
      addr.sin_family = AF_INET;
      addr.sin_addr.s_addr = getAddress(interface);
      addr.sin_port = htons(port);
      if (setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &reuse_addr, sizeof(reuse_addr)) < 0) {
        close(sock);
        error("Unable to setsockopt SO_REUSEADDR");
      }

      /* ... Custom socket option values set here ... */
      max_index = MIN(so_index, ZEN_MAX_SO_OPTIONS);
      for(i=0; i <= max_index; i++) {
        so_option = so_setting[i].code;
        so_value = so_setting[i].value;
        if(setsockopt(sock, SOL_SOCKET, so_option, &so_value, sizeof(so_value))) {
          close(sock);
          error("Unable to setsockopt");
        }
      }

      if (bind(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close(sock);
        error("Unable to bind to listen port (error code %d)", errno);
      }
      
    }
  
  }

  /* No need to be root any more */
  if (getuid() != 0) {
      setuid(getuid());
  } else {
      error("Unable to find a user to become");
  }

  if (optind >= argc) {
    usage(argv[0]);
  }
  
  sprintf(filenoString, "%d", sock);
  if (strlen(filenoString) > strlen(replace)) {
    error("What are you up to?");
  }
  args = (char**)malloc(sizeof(char*)*(argc - optind + 1));

  if (!args) {
    error("Out of memory");
  }

  for (i = optind, c = 0; i < argc; i++, c++) {
    char * p = strstr(argv[i], replace);
    if (p) {
      strcpy(p, filenoString);
      strcpy(p + strlen(filenoString), p + strlen(replace));
    }

    args[c] = argv[i];
  }

  args[c] = 0;
  {
      char libdir[1000];
      snprintf(libdir, sizeof(libdir)-1, "LD_LIBRARY_PATH=%s/lib", getenv("ZENHOME"));
      if (putenv(libdir) != 0) {
	  perror("Unable to set LD_LIBRARY_PATH");
      }
      if (execv(args[0], args) < 0) {
	perror("exec fails");
      }
  }

  free(args);
  exit(EXIT_SUCCESS);

  return 0;
}
