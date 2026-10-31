#include <libcdr/libcdr.h>
#include <librevenge/librevenge.h>
#include <librevenge-stream/librevenge-stream.h>
#include <librevenge-generators/librevenge-generators.h>
#include <iostream>
int main(int argc,char**argv){librevenge::RVNGFileStream input(argv[1]);librevenge::RVNGStringVector output;librevenge::RVNGSVGDrawingGenerator painter(output,"");if(!libcdr::CDRDocument::parse(&input,&painter))return 1;for(unsigned i=0;i<output.size();i++)std::cout<<output[i].cstr();}
