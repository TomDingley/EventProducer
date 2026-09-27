#include "Pythia8/Pythia.h"
#include <iomanip>
#include <iostream>

static void printWeights(const Pythia8::Pythia& pythia, const char* stage) {
  const auto names = pythia.info.weightNameVector();
  const auto values = pythia.info.weightValueVector();
  std::cout << stage << " names=" << names.size() << " values=" << values.size() << '\n';
  for (size_t i = 0; i < names.size() && i < values.size(); ++i) {
    std::cout << i << " " << names[i] << " " << std::setprecision(17) << values[i] << '\n';
  }
}

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  Pythia8::Pythia pythia;
  pythia.readString("Beams:frameType = 4");
  pythia.readString(std::string("Beams:LHEF = ") + argv[1]);
  pythia.readString("Beams:setProductionScalesFromLHEF = off");
  pythia.readString("Next:numberShowEvent = 0");
  pythia.readString("Next:numberShowInfo = 0");
  if (!pythia.init()) return 3;
  printWeights(pythia, "after_init");
  if (!pythia.next()) return 4;
  printWeights(pythia, "after_next");
}
