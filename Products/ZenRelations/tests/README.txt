ZenRelations Testing System

ZenRelations uses the following schema to perform tests on relationships:
     


       devices           location ----------
       --------------------------| Location |
      | *                      1  ----------
      |
  --------  devices        groups -------
 | Device |----------------------| Group |
  --------  *                  *  -------
   ^   |
   |   | device            interfaces  -------------
   |    ----------------------------<>| IpInterface |
   |       1                     *     -------------
   |
  --------    1               1   -------
 | Server |----------------------| Admin |
  --------  server         admin  -------

