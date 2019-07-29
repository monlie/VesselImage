import numpy as np
import networkx as nx
import re
from queue import Queue


class FilamentNode(object):
    
    def __init__(self, coord):
        self.coordinate = coord
        self.neighboors = []
        self.length = []
        self.width = []
    
    def __hash__(self):
        return self.coordinate.__hash__()
    
    def __str__(self):
        return 'FilamentNode' + str(self.coordinate)

    # MAGIC
    __repr__ = __str__
    

class Filament(object):

    def __init__(self, curves):
        # attrs
        self.curves = curves
        self.node_buffer = {}
        self.nxgraph = nx.Graph()
        self.has_layers = False
        # add edges
        for curve in curves:
            # nodes
            origin = self.get_node(curve[0, :3])
            tail = self.get_node(curve[-1, :3])
            # link nodes
            origin.neighboors.append(tail)
            tail.neighboors.append(origin)
            # average width
            width = curve[:, -1].mean()
            origin.width.append(width)
            tail.width.append(width)
            # curve length
            length = np.sqrt(np.square(np.diff(curve[:, :3], axis=0)).sum(axis=1)).sum()
            origin.length.append(length)
            tail.length.append(length)
            # networkx
            self.nxgraph.add_edge(origin, tail, width=width, length=length)
        self.ordered_nodes = np.array(list(self.node_buffer))

    def get_node(self, coord):
        if isinstance(coord, int):
            coord = self.ordered_nodes[coord]
        coord = tuple(coord)
        if coord not in self.node_buffer:
            self.node_buffer[coord] = FilamentNode(coord)
        return self.node_buffer[coord]

    def plot_network(self, layer_strt=False):
        if layer_strt and not self.has_layers:
            raise RuntimeError("layer structure must be generated after dfs")
        pos = nx.spring_layout(self.nxgraph)
        nx.draw(self.nxgraph, pos, node_size=20, node_color="darkorange", edge_color="firebrick")

    def dfs(self, coord):
        root = self.get_node(coord)
        viewed = set([root])
        q = Queue()
        pair = (root, 0)
        q.put(pair)
        self.layer_list = [pair]
        while not q.empty():
            node, depth = q.get()
            for tmp in node.neighboors:
                if tmp not in viewed:
                    viewed.add(tmp)
                    pair = (tmp, depth + 1)
                    q.put(pair)
                    self.layer_list.append(pair)       
        # list2dict
        self.layer_dict = {}
        for node, layer in self.layer_list:
            if layer not in self.layer_dict:
                self.layer_dict[layer] = []
            self.layer_dict[layer].append(node)
        self.has_layers = True
                    
    def get_nodes_with_depth(self, depth):
        return self.layer_dict[depth]

    def plot_2d(self, ax, layer_strt=False, font="roboto", **attrs):
        if layer_strt and not self.has_layers:
            raise RuntimeError("layer structure must be generated after dfs")
        for data in self.curves:
            ax.plot(data[:, 0], data[:, 1], linewidth=2, color='firebrick')
        # draw layer labels
        if layer_strt:
            # draw bifurcations
            coords = np.array([c[0].coordinate[:2] for c in self.layer_list])
            ax.scatter(coords[:, 0], coords[:, 1], **attrs)
            # draw labels
            l = [c[1] for c in self.layer_list]
            for coo, li in zip(coords, l):
                ax.text(*coo, li, fontsize=8, family=font, weight="heavy")
        else:
            ax.scatter(self.ordered_nodes[:, 0], self.ordered_nodes[:, 1], **attrs)
            for idx, node in enumerate(self.ordered_nodes):
                ax.text(*node[:2], idx, fontsize=8, family=font, weight="heavy")
    
    def plot_3d(self, ax, layer_strt=False, font="roboto", **attrs):
        if layer_strt and not self.has_layers:
            raise RuntimeError("layer structure must be generated after dfs")
        # draw curves
        for data in self.curves:
            ax.plot(data[:, 0], data[:, 1], data[:,2],
                    linewidth=2, color='firebrick')
        # draw layer labels
        if layer_strt:
            # draw bifurcations
            coords = np.array([c[0].coordinate for c in self.layer_list])
            ax.scatter(coords[:, 0], coords[:, 1], coords[:, 2], **attrs)
            # draw labels
            l = [c[1] for c in self.layer_list]
            for coo, li in zip(coords, l):
                ax.text(*coo, li, fontsize=8, family=font, weight="heavy")
        else:
            ax.scatter(self.ordered_nodes[:, 0], self.ordered_nodes[:, 1], self.ordered_nodes[:, 2], **attrs)
            for idx, node in enumerate(self.ordered_nodes):
                ax.text(*node[:3], idx, fontsize=8, family=font, weight="heavy")


def code2mat(code):
    pattern = r"pt3dadd\((\d+?.\d+?,\d+?.\d+?,\d+?.\d+?\,\d+?.\d+?,\d)\)"
    code = re.findall(pattern, code)
    data = np.array([list(map(float, c.split(",")))[:4] for c in code])
    return data


def get_components(path):
    with open(path, 'r') as f:
        text = f.read()
    pattern = re.compile(r"filament_(\d+?)\[\d+?\] \{(.+?)\}", re.S)
    components = {}
    for idx, code in re.findall(pattern, text):
        if idx not in components:
            components[idx] = []
        components[idx].append(code2mat(code))
    return components