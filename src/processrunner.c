#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/wait.h>
#include <signal.h>

// Structure to hold process information
typedef struct {
    char process_name[50];
    char command[256];
    pid_t pid;
    FILE *log_file;
} Process;

Process processes[10]; // Assuming a maximum of 10 processes
int num_processes = 0;

// Signal handler function
void handle_signal(int sig) {
    if (sig == SIGINT || sig == SIGTERM) {
        printf("Received signal %d. Shutting down processes...\n", sig);
        // Send termination signal to all child processes
        for (int i = 0; i < num_processes; i++) {
            if (processes[i].pid > 0) {
                kill(processes[i].pid, SIGTERM);
            }
        }
    }
}

int main() {
      FILE *procfile = fopen("Procfile", "r");
    if (!procfile) {
        perror("Error opening Procfile");
        return 1;
    }

    char line[512];
    while (fgets(line, sizeof(line), procfile)) {
        // Remove trailing newline character if present
        line[strcspn(line, "\n")] = 0;

        // Skip empty lines or lines starting with '#' (comments)
        if (line == '\0' || line[0] == '#') {
            continue;
        }

        // Find the colon delimiter
        char *colon = strchr(line, ':');

        // Check if the colon is found and is not the first character
        if (colon && colon > line) {
            // Null-terminate the process name string
            *colon = '\0';
            char *process_name = line;

            // Extract the command string (skipping the colon and any leading spaces)
            char *command = colon + 1;
            while (*command == ' ') {
                command++;
            }

            // Store the process name and command in the 'processes' array
            if (num_processes < 10) {
                strncpy(processes[num_processes].process_name, process_name, sizeof(processes[num_processes].process_name) - 1);
                processes[num_processes].process_name[sizeof(processes[num_processes].process_name) - 1] = '\0'; // Ensure null termination
                strncpy(processes[num_processes].command, command, sizeof(processes[num_processes].command) - 1);
                processes[num_processes].command[sizeof(processes[num_processes].command) - 1] = '\0'; // Ensure null termination
                processes[num_processes].pid = 0; // Initialize pid
                processes[num_processes].log_file = NULL; // Initialize log file pointer
                num_processes++;
            } else {
                fprintf(stderr, "Error: Maximum number of processes exceeded.\n");
                // Handle this error appropriately (e.g., exit or break)
                break;
            }
        } else {
	  if(*line)
            fprintf(stderr, "Warning: Skipping invalid line in Procfile: [%s]\n", line);
        }
    }
    fclose(procfile);
    /*
    // 1. Procfile Parsing (simplified)
    FILE *procfile = fopen("Procfile", "r");
    if (!procfile) {
        perror("Error opening Procfile");
        return 1;
    }

    char line[512];
    while (fgets(line, sizeof(line), procfile)) {
        // Parse the line to extract process name and command
        // ... (implementation details omitted for brevity)
        // Store in the 'processes' array
    }
    fclose(procfile);
    */
    // 2. Process Routing and Execution
    for (int i = 0; i < num_processes; i++) {
        processes[i].pid = fork();
        if (processes[i].pid == 0) { // Child process
            // 3. Separate Logs
            char log_filename[100];
            sprintf(log_filename, "%s.log", processes[i].process_name);
            processes[i].log_file = fopen(log_filename, "w");
            if (processes[i].log_file) {
                dup2(fileno(processes[i].log_file), STDOUT_FILENO); // Redirect stdout
                dup2(fileno(processes[i].log_file), STDERR_FILENO); // Redirect stderr
                fclose(processes[i].log_file); // Close the original file descriptor
            }

            // Execute the command
            char *args[] = {"/bin/sh", "-c", processes[i].command, NULL}; // Execute using sh -c
            execvp("/bin/sh", args);
            perror("execvp failed"); // Should not reach here if execvp succeeds
            exit(EXIT_FAILURE);
        } else if (processes[i].pid < 0) {
            perror("fork failed");
            return 1;
        }
    }

    // 4. Signal Handling
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    printf("All processes started...\n");

    // Wait for child processes to finish (or be terminated)
    for (int i = 0; i < num_processes; i++) {
        if (processes[i].pid > 0) {
            waitpid(processes[i].pid, NULL, 0);
        }
    }

    return 0;
}
