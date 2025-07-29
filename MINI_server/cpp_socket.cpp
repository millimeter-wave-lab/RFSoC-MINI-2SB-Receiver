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

    std::vector<uint8_t> send_request(const std::string& request, size_t expected_bytes) {
        if (send(sockfd, request.c_str(), request.length(), 0) < 0) {
            throw std::runtime_error("Failed to send request");
        }
        
        std::vector<uint8_t> buffer;
        buffer.reserve(expected_bytes);
        size_t total_received = 0;
        
        while (total_received < expected_bytes) {
            std::vector<uint8_t> chunk(32768);  // Tamaño de bloque arbitrario
            int valread = recv(sockfd, chunk.data(), chunk.size(), 0);
            if (valread <= 0) {
                throw std::runtime_error("Connection closed or failed while receiving data");
            }
            buffer.insert(buffer.end(), chunk.begin(), chunk.begin() + valread);
            total_received += valread;
        }
        
        return buffer;
    }
    

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
        .def("send_request", [](CPPSocket& self, const std::string& request, size_t expected_bytes) {
            std::vector<uint8_t> data = self.send_request(request, expected_bytes);
            return pybind11::bytes(reinterpret_cast<const char*>(data.data()), data.size());
        }, pybind11::arg("request"), pybind11::arg("expected_bytes"), pybind11::return_value_policy::move);
        
}