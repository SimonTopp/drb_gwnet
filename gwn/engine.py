import torch
import torch.optim as optim
from gwn.model import *
#import gwn.util as util

class trainer():
    def __init__(self, scaler, in_dim, num_nodes, lrate, device, supports, aptinit, out_dim, kernel,
                 blocks, layers, scale_y, nhid=32, wdecay=0.0001, dropout=0.3, gcn_bool=True, addaptadj=True):
        self.model = gwnet(device, num_nodes, dropout, supports=supports, gcn_bool=gcn_bool, addaptadj=addaptadj,
                           aptinit=aptinit, in_dim=in_dim, out_dim=out_dim, residual_channels=nhid,
                           dilation_channels=nhid, skip_channels=nhid * 8, end_channels=nhid * 16, kernel_size=kernel,
                           blocks=blocks, layers=layers)
        #skip and end were 8 and 16 respectively
        self.model.to(device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=lrate, weight_decay=wdecay)
        self.loss = util.rmse #was mae
        self.scaler = scaler
        self.clip = 3
        self.scale_y = scale_y
        self.scheduler = optim.lr_scheduler.LambdaLR(
            self.optimizer, lr_lambda=lambda epoch: 0.97 ** epoch)

    def train(self, input, real_val):
        self.model.train()
        self.optimizer.zero_grad()
        input = nn.functional.pad(input,(1,0,0,0))
        #input = self.scaler.transform(input)
        output = self.model(input)
        output = output.transpose(1,3)
        #output = [batch_size,12,num_nodes,1]
        real = torch.unsqueeze(real_val,dim=1)
        predict = output

        assert real.shape == predict.shape, "Output dims not right, increase kernel or layer size"

        loss = self.loss(predict, real)
        loss.backward()
        if self.clip is not None:
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.clip)
        self.optimizer.step()
        if self.scale_y:
            real = self.scaler.inverse_transform(real.cpu())
            predict = self.scaler.inverse_transform(output.detach().cpu())
            metrics = util.metric(predict,real)
        else:
            metrics = util.metric(predict,real)
        return metrics

    def eval(self, input, real_val):
        self.model.eval()
        input = nn.functional.pad(input,(1,0,0,0))
        #input = self.scaler.transform(input)
        output = self.model(input)
        output = output.transpose(1,3)
        #output = [batch_size,12,num_nodes,1]
        real = torch.unsqueeze(real_val,dim=1)
        predict = output
        loss = self.loss(predict, real)
        if self.scale_y:
            #real = real.to(type=torch.float64)
            #real = self.scaler.inverse_transform(real)
            predict = self.scaler.inverse_transform(output.detach().cpu()).float()
            metrics = util.metric(predict,real.cpu())
        else:
            metrics = util.metric(predict,real)
        return metrics