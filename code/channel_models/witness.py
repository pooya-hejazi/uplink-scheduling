"""An exact checker validates whatever the assignment routines return."""
import ast,inspect,hashlib
import numpy as np,networkx as nx
from scipy.optimize import linear_sum_assignment
import networkx.algorithms.matching as nm
src=inspect.getsource(nm.max_weight_matching)
if hashlib.sha256(src.encode()).hexdigest()!='41930910962d79c5da2da89788ead7819730daccb2858d72df3df7c55d893ee1': raise RuntimeError('unsupported NetworkX blossom implementation; pinned 3.4.2 required')
tree=ast.parse(src); fn=tree.body[0]; fn.decorator_list=[]
fn.body[-1].value=ast.parse('(matching_dict_to_set(mate), dualvar, [(tuple(sorted(b.leaves())),z) for b,z in blossomdual.items() if z>0])',mode='eval').body
ns=vars(nm).copy(); exec(compile(ast.fix_missing_locations(tree),'<pinned-blossom-with-witness>','exec'),ns)
def assignment(A):
    A=np.asarray(A,dtype=np.int64); n=len(A)
    if A.shape!=(n,n) or np.max(np.abs(A.astype(float)))>=2**48: raise ArithmeticError('assignment range')
    rows,cols=linear_sum_assignment(A,maximize=True)
    if not np.array_equal(rows,np.arange(n)) or len(set(cols))!=n: raise ArithmeticError('bijection')
    # Bellman-Ford potentials on the assigned columns, exact bounded integers.
    b=np.zeros(n,dtype=np.int64); selected=A[rows,cols]
    for _ in range(n):
        z=np.maximum(b,(A+(b[cols]-selected)[:,None]).max(0))
        if np.array_equal(z,b): break
        b=z
    y=selected-b[cols]
    if np.any(y[:,None]+b<A) or int(y.sum()+b.sum())!=int(selected.sum()): raise ArithmeticError('invalid Hungarian dual')
    return cols,y,b
def check(k,I,J,w,pairs,y,z):
    if sorted(np.asarray(pairs).reshape(-1).tolist())!=list(range(k)) or len(y)!=k: raise ArithmeticError('nonperfect matching')
    if any(abs(int(v))>=2**52 for v in y) or sum(abs(int(v)) for _,v in z)>=2**52: raise ArithmeticError('dual range')
    lhs=y[I]+y[J]; objective=sum(map(int,y))
    for B,price in z:
        if len(set(B))!=len(B) or len(B)<3 or len(B)%2!=1 or not all(0<=u<k for u in B) or price<0: raise ArithmeticError('invalid odd set')
        zmask=np.zeros(k,bool); zmask[list(B)]=True
        lhs=lhs+2*int(price)*(zmask[I]&zmask[J]); objective+=2*(len(B)//2)*int(price)
    ix=edgeid(k,pairs[:,0],pairs[:,1]); value=sum(int(v) for v in w[ix])
    if np.any(lhs<2*w) or objective!=2*value: raise ArithmeticError('invalid blossom witness')
    return value
def edgeid(k,i,j):
    u,v=np.minimum(i,j),np.maximum(i,j); return u*(2*k-u-1)//2+v-u-1
def blossom(k,I,J,w):
    w=np.asarray(w,dtype=np.int64)
    if not w.size or np.max(np.abs(w.astype(float)))>=2**46: raise ArithmeticError('blossom range')
    # Fast common case: integral optimum of the assignment relaxation. Symmetrize its dual.
    A=np.full((k,k),-(2**47),dtype=np.int64); A[I,J]=A[J,I]=w
    col=linear_sum_assignment(A,maximize=True)[1]; used=set(); pairs=[]
    for i in range(k):
        if i in used: continue
        cyc=[]; j=i
        while j not in used: used.add(j);cyc.append(j);j=col[j]
        if len(cyc)%2: break
        pairs+=list(zip(cyc[::2],cyc[1::2]))
    if len(pairs)==k//2:
        _,a,b=assignment(A); y=a+b; z=[]; pairs=np.sort(pairs,axis=1)
        try: value=check(k,I,J,w,pairs,y,z);return pairs,y,z,value
        except ArithmeticError: pass
    G=nx.Graph(); G.add_weighted_edges_from(zip(I.tolist(),J.tolist(),w.tolist()))
    m,v,z=ns['max_weight_matching'](G,maxcardinality=True)
    pairs=np.array(sorted(tuple(sorted(vv)) for vv in m),int)
    y=np.array([v[i] for i in range(k)],np.int64)
    return pairs,y,z,check(k,I,J,w,pairs,y,z)
def repair(H,I,J,alpha):
    bp=np.max(H-(alpha[I]+alpha[J])[:,None],axis=0)
    if np.any((alpha[I]+alpha[J])[:,None]+bp<H): raise ArithmeticError('invalid P3 repair')
    return bp,int(alpha.sum()+bp.sum())

