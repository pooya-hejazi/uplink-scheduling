"""Three residual factor, pair, tone and user updates; shared box head at root and children."""
import math,torch
from torch import nn
import torch.nn.functional as F
D=32
def mlp(n,m):return nn.Sequential(nn.Linear(n,D),nn.ReLU(),nn.Linear(D,m))
class Layer(nn.Module):
    def __init__(self):
        super().__init__();self.f=mlp(5*D,D);self.e=mlp(2*D,D);self.t=mlp(2*D,D);self.u=mlp(2*D,D)
    def forward(self,f,u,e,t,I,J):
        B,E,S,W=f.shape
        s=t[:,None].expand(-1,E,-1,-1)
        sym=(u[:,I]+u[:,J])[:,:,None].expand(-1,-1,S,-1)
        diff=abs(u[:,I]-u[:,J])[:,:,None].expand(-1,-1,S,-1)
        f=f+self.f(torch.cat([f,e[:,:,None].expand(-1,-1,S,-1),s,sym,diff],-1))
        e=e+self.e(torch.cat([e,f.mean(2)],-1)); t=t+self.t(torch.cat([t,f.mean(1)],-1))
        msg=torch.zeros_like(u).index_add_(1,I,e).index_add_(1,J,e)/(u.shape[1]-1)
        return f,u+self.u(torch.cat([u,msg],-1)),e,t
class Net(nn.Module):
    def __init__(self):
        super().__init__();self.f=nn.Linear(7,D);self.layers=nn.ModuleList([Layer() for _ in range(3)])
        self.uh=mlp(D,2);self.th=mlp(D,1);self.eh=mlp(D,1);self.lh=mlp(D,1);self.bh=mlp(D+4,3)
    def box(self,f,coords):
        coord=f.new_tensor(coords).expand(*f.shape[:-1],4)
        return self.bh(torch.cat([f,coord],-1))
    def forward(self,x,encoder_event=None):
        B,E,S,_=x.shape;k=2*S;I,J=torch.triu_indices(k,k,1,device=x.device)
        f=torch.relu(self.f(x)); e=f.mean(2); t=f.mean(1);u=f.new_zeros(B,k,D).index_add_(1,I,e).index_add_(1,J,e)/(k-1)
        for layer in self.layers:f,u,e,t=layer(f,u,e,t,I,J)
        if encoder_event is not None:encoder_event.record()
        uh=self.uh(u); a=uh[:,:,1];b=self.th(t).squeeze(-1)
        root=self.box(f,[0,1,0,1])
        # Skip connection uses only observed equal-power features (no teacher or true optimum at inference).
        hi=(x[:,:,:,0]+x[:,:,:,1])*2.5; lo=(x[:,:,:,0]-x[:,:,:,1])*2.5
        rate=hi+lo+2*torch.log1p(-torch.clamp(x[:,:,:,2]*(-torch.expm1(-hi))*(-torch.expm1(-lo)),max=.9999999))
        return {'score':rate+.1*self.eh(f).squeeze(-1),'p':.05+.15*torch.sigmoid(uh[:,:,0]),'alpha':a-a.mean(1,keepdim=True),'beta':b-b.mean(1,keepdim=True),'lam':12*torch.sigmoid(self.lh(u.mean(1)).reshape(B)),'anchor':.05+.15*root[:,:,:,0:2].sigmoid(),'priority':root[:,:,:,2],'f':f,'I':I,'J':J}
def batch_loss(model,rows):
    import numpy as np
    def stack(key):return torch.from_numpy(np.stack([a[key] for a in rows])).to('cuda')
    x=stack('x');d=model(x);B,E,S,_=x.shape
    target=torch.zeros_like(d['score']); bi=torch.arange(B,device='cuda')[:,None];si=torch.arange(S,device='cuda')[None,:]
    target[bi,stack('e').long(),si]=1
    # Center logits per example; equally weight positives and negatives.
    z=d['score']-d['score'].mean((1,2),keepdim=True)
    loss=(F.softplus(-z)*target).sum()/target.sum()/2+(F.softplus(z)*(1-target)).sum()/(1-target).sum()/2
    loss=loss+((d['p']-stack('p'))/.15).square().mean()+((d['anchor']-stack('anchor'))/.15).square().mean()
    for name in ['alpha','beta']:loss=loss+((d[name]-stack(name))/4).square().mean()
    loss=loss+((d['lam']-stack('lam'))/10).square().mean()
    coords=[];sg=[];rootpairs=[]
    for b,row in enumerate(rows):
        ids=row['rank_id'];coords.append(d['f'][b].reshape(-1,D)[torch.as_tensor(ids,device='cuda')]);sg.extend(row['rank_sign'])
        ids=row['visited'];targetv=row['root_delta'];order=np.argsort(targetv);n=len(order)//2;mask=targetv[order[-n:]]-targetv[order[:n]]>1e-10
        if n and mask.any():
            pr=d['priority'][b].reshape(-1);rootpairs.append(pr[torch.as_tensor(ids[order[-n:][mask]],device='cuda')]-pr[torch.as_tensor(ids[order[:n][mask]],device='cuda')])
    if len(sg):
        v=torch.cat(coords);a=model.box(v,[0,.5,0,1])[:,2];b=model.box(v,[.5,1,0,1])[:,2]
        loss=loss+F.softplus(-torch.tensor(sg,device='cuda')*(a-b)).mean()
    if rootpairs:loss=loss+F.softplus(-torch.cat(rootpairs)).mean()
    return loss
SEEDS=[1729,2718,3141]

