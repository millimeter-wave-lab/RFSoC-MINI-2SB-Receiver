#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>
#include <iostream>
#include <string>
#include <vector>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>

class CPPSocket {
public:
    CPPSocket(const std::string& host, int port) {
        sockfd = socket(AF_INET, SOCK_STREAM, 0);
        if (sockfd < 0) {
            throw std::runtime_error("Failed to create socket");
        }
        
        server_addr.sin_family = AF_INET;
        server_addr.sin_port = htons(port);
        if (inet_pton(AF_INET, host.c_str(), &server_addr.sin_addr) <= 0) {
            throw std::runtime_error("Invalid address/ Address not supported");
        }
        
        if (connect(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
            throw std::runtime_error("Connection failed");
        }
    }

    std::vector<uint8_t> send_request(const std::string& request) {
        // std::string modified_request = request + "\n"; // Create a modifiable copy
        if (send(sockfd, request.c_str(), request.length(), 0) < 0) {
            throw std::runtime_error("Failed to send request");
        }
        
        std::vector<uint8_t> buffer(20000); // Allocate buffer for receiving raw data
        int valread = recv(sockfd, buffer.data(), buffer.size(), 0);
        if (valread < 0) {
            throw std::runtime_error("Failed to receive response");
        }

        buffer.resize(valread); // Trim to actual received size
        return buffer;

    }
    //     char buffer[4096] = {0};
    //     int valread = recv(sockfd, buffer, 4096, 0);
    //     if (valread < 0) {
    //         throw std::runtime_error("Failed to receive response");
    //     }
    //     return std::string(buffer, valread);
    // }

    ~CPPSocket() {
        close(sockfd);
    }

private:
    int sockfd;
    struct sockaddr_in server_addr;
};

PYBIND11_MODULE(cpp_socket, m) {
    pybind11::class_<CPPSocket>(m, "CPPSocket")
        .def(pybind11::init<const std::string&, int>())
        .def("send_request", [](CPPSocket& self, const std::string& request) {
            std::vector<uint8_t> data = self.send_request(request);
            return pybind11::bytes(reinterpret_cast<const char*>(data.data()), data.size());
        }, pybind11::return_value_policy::move);
}