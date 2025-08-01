#include <iostream>
#include <iomanip>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <cstdint>
#include <sys/socket.h>
#include <netinet/in.h>
#include <cstring>
#include <unordered_map>
#include <mutex>
#include <sstream>

#define BRAM_SIZE_LARGE 0x1000
#define BRAM_SIZE_SMALL 0x100
#define ACC_CNT_SIZE 4
#define PORT 12345

std::unordered_map<std::string, uintptr_t> bram_addresses = {
    // BRAMs grandes
    {"synth0_0", 0xA0140000}, {"synth0_1", 0xA0141000}, {"synth0_2", 0xA0142000}, {"synth0_3", 0xA0143000},
    {"synth0_4", 0xA0144000}, {"synth0_5", 0xA0145000}, {"synth0_6", 0xA0146000}, {"synth0_7", 0xA0147000},
    {"synth1_0", 0xA0148000}, {"synth1_1", 0xA0149000}, {"synth1_2", 0xA014A000}, {"synth1_3", 0xA014B000},
    {"synth1_4", 0xA014C000}, {"synth1_5", 0xA014D000}, {"synth1_6", 0xA014E000}, {"synth1_7", 0xA014F000},

    // BRAMs pequeñas
    {"re_bin_synth0_0", 0xA0150000}, {"re_bin_synth0_1", 0xA0150100}, {"re_bin_synth0_2", 0xA0150200}, {"re_bin_synth0_3", 0xA0150300},
    {"re_bin_synth0_4", 0xA0150400}, {"re_bin_synth0_5", 0xA0150500}, {"re_bin_synth0_6", 0xA0150600}, {"re_bin_synth0_7", 0xA0150700},
    {"re_bin_synth1_0", 0xA0150800}, {"re_bin_synth1_1", 0xA0150900}, {"re_bin_synth1_2", 0xA0150A00}, {"re_bin_synth1_3", 0xA0150B00},
    {"re_bin_synth1_4", 0xA0150C00}, {"re_bin_synth1_5", 0xA0150D00}, {"re_bin_synth1_6", 0xA0150E00}, {"re_bin_synth1_7", 0xA0150F00},

    // Contador
    {"acc_cnt", 0xA0151000}
};

std::unordered_map<std::string, void*> mapped_brams;
std::mutex bram_mutex;
int fd = -1;

bool init_bram() {
    fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (fd < 0) {
        std::cerr << "Error al abrir /dev/mem" << std::endl;
        return false;
    }

    for (const auto& pair : bram_addresses) {
        const std::string& name = pair.first;
        uintptr_t phys_addr = pair.second;

        size_t size;
        if (name == "acc_cnt") {
            size = ACC_CNT_SIZE;
        } else if (name.find("re_bin_") == 0) {
            size = BRAM_SIZE_SMALL;
        } else {
            size = BRAM_SIZE_LARGE;
        }

        // Alinear dirección a página (usualmente 0x1000)
        uintptr_t aligned_addr = phys_addr & ~(uintptr_t)(0xFFF);
        uintptr_t offset_in_page = phys_addr - aligned_addr;
        size_t map_size = offset_in_page + size;

        void* ptr = mmap(nullptr, map_size, PROT_READ, MAP_SHARED, fd, aligned_addr);
        if (ptr == MAP_FAILED) {
            std::cerr << "Error al mapear BRAM: " << name << std::endl;
            return false;
        }

        // Guardar el puntero ajustado (no el alineado)
        mapped_brams[name] = static_cast<uint8_t*>(ptr) + offset_in_page;
    }

    return true;
}


void cleanup_bram() {
    for (const auto& pair : mapped_brams) {
        size_t size;
        if (pair.first == "acc_cnt") {
            size = ACC_CNT_SIZE;
        } else if (pair.first.find("re_bin_") == 0) {
            size = BRAM_SIZE_SMALL;
        } else {
            size = BRAM_SIZE_LARGE;
        }

        munmap(pair.second, size);
    }

    if (fd >= 0) {
        close(fd);
    }
}

void send_bram_data(int client_fd, const std::string& bram_name, size_t offset, size_t length) {
    std::lock_guard<std::mutex> lock(bram_mutex);

    auto it = mapped_brams.find(bram_name);
    if (it == mapped_brams.end()) {
        std::cerr << "BRAM no encontrada: " << bram_name << std::endl;
        send(client_fd, "ERROR", 5, 0);
        return;
    }

    size_t max_size;
    if (bram_name == "acc_cnt") {
        max_size = ACC_CNT_SIZE;
    } else if (bram_name.find("re_bin_") == 0) {
        max_size = BRAM_SIZE_SMALL;
    } else {
        max_size = BRAM_SIZE_LARGE;
    }

    if (offset >= max_size) {
        send(client_fd, "ERROR", 5, 0);
        return;
    }

    if (offset + length > max_size) {
        length = max_size - offset;
    }

    send(client_fd, static_cast<uint8_t*>(it->second) + offset, length, 0);
}

int main() {
    if (!init_bram()) return -1;

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        std::cerr << "Error al crear el socket" << std::endl;
        return -1;
    }

    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(PORT);

    if (bind(server_fd, (sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        std::cerr << "Error al enlazar el socket" << std::endl;
        return -1;
    }

    if (listen(server_fd, 1) < 0) {
        std::cerr << "Error al escuchar conexiones" << std::endl;
        return -1;
    }

    std::cout << "Servidor esperando una conexión en el puerto " << PORT << "..." << std::endl;

    sockaddr_in client_addr;
    socklen_t client_len = sizeof(client_addr);
    int client_fd = accept(server_fd, (sockaddr*)&client_addr, &client_len);
    if (client_fd < 0) {
        std::cerr << "Error al aceptar conexión" << std::endl;
        return -1;
    }

    std::cout << "Cliente conectado." << std::endl;

    while (true) {
        char buffer[128] = {0};
        ssize_t bytes = recv(client_fd, buffer, sizeof(buffer) - 1, 0);
        if (bytes <= 0) break;

        std::string request(buffer);
        std::istringstream iss(request);
        std::string bram_name;
        size_t offset = 0, length = 0;

        if (!(iss >> bram_name >> offset >> length)) {
            std::cerr << "Formato de solicitud inválido" << std::endl;
            send(client_fd, "ERROR", 5, 0);
            continue;
        }

        send_bram_data(client_fd, bram_name, offset, length);
    }

    std::cout << "Cliente desconectado." << std::endl;
    cleanup_bram();
    close(client_fd);
    close(server_fd);
    return 0;
}
