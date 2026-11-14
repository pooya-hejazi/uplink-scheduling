#include <lemon/list_graph.h>
#include <lemon/matching.h>
#include <cstdint>
using namespace lemon;
using I64 = long long;
extern "C" __declspec(dllexport) int exact(int k, const I64* weights, int* mate, I64* y4, unsigned long long* masks, I64* z4) {
  if (k<2 || k>64 || (k&1)) return -1;
  ListGraph graph;
  ListGraph::Node nodes[64];
  for(int i=0;i<k;++i) nodes[i]=graph.addNode();
  ListGraph::EdgeMap<I64> w(graph);
  int e=0;
  for(int i=0;i<k;++i) for(int j=i+1;j<k;++j) w[graph.addEdge(nodes[i],nodes[j])]=weights[e++];
  typedef MaxWeightedPerfectMatching<ListGraph,ListGraph::EdgeMap<I64>> M;
  static_assert(M::dualScale==4,"unexpected dual scale");
  M result(graph,w);
  if(!result.run()) return -2;
  for(int i=0;i<k;++i) { mate[i]=graph.id(result.mate(nodes[i]));y4[i]=result.nodeValue(nodes[i]); }
  int n=0;
  for(int b=0;b<result.blossomNum();++b) {
    auto z=result.blossomValue(b);
    if(z<=0) continue;
    if(n>=k) return -3;
    unsigned long long mask=0;
    for(M::BlossomIt v(result,b);v!=INVALID;++v) mask|=1ULL<<graph.id(v);
    masks[n]=mask;z4[n++]=z;
  }
  return n;
}

