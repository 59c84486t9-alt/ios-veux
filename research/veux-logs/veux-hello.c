#include <errno.h>
#include <fcntl.h>
#include <os/log.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int
main(void)
{
	static const char message[] =
	    "VEUX USERLAND HELLO: LaunchDaemon reached main()\n"
	    "VEUX_FB_GREEN_BLOCK\n";
	os_log_t log = os_log_create("org.veux.bringup", "hello");
	os_log_with_type(log, OS_LOG_TYPE_DEFAULT, "%{public}s", message);

	int console = open("/dev/console", O_WRONLY | O_NOCTTY);
	int console_errno = 0;
	if (console >= 0) {
		(void)write(console, message, sizeof(message) - 1);
		(void)close(console);
	} else {
		console_errno = errno;
	}

	int fd = open("/private/var/log/veux-hello.log",
	    O_WRONLY | O_CREAT | O_APPEND, 0644);
	if (fd >= 0) {
		char result[160];
		int len = snprintf(result, sizeof(result),
		    "console_open_errno=0x%x %s", console_errno, message);
		if (len > 0) {
			(void)write(fd, result, (size_t)len);
		}
		(void)close(fd);
	}
	return console_errno == 0 ? 0 : 1;
}
