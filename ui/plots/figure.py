import plotly.graph_objects as go
import plotly.express as px

class DataPlot():
    def __init__(self, title:str|None = None):
        self.title = title

    def empty(self) -> bool:
        raise NotImplementedError

    def _build(self) -> go.Figure:
        raise NotImplementedError            

    def figure(self) -> go.Figure:
        fig = go.Figure() if self.empty() else self._build()
        return self._style(fig)

    def _style(self, fig: go.Figure) -> go.Figure:
        fig.update_layout(title=self.title, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", template="plotly_dark")
        return fig

class ScatterPlot(DataPlot):
    def __init__(self, x:list|None=None, y:list|None=None, labelx:str|None=None, labely:str|None=None, hover:list|None=None, hover_name:str|None=None, 
                 xrange:int|None=None, yrange:int|None=None, title:str|None=None):
        super().__init__(title)
        self.x, self.y = x, y
        self.labelx, self.labely = labelx, labely
        self.hover = hover
        self.hover_name = hover_name
        self.xrange, self.yrange = xrange, yrange


    def empty(self):
        return (self.x is None and self.y is None)

    def _build(self):
        hover = {f"{self.hover_name}": self.hover} if self.hover is not None else None
        fig = px.scatter(x=self.x, y=self.y, hover_data=hover, labels={"x": self.labelx, "y": self.labely})
        if self.xrange:
            fig.update_xaxes(range=self.xrange)
        if self.yrange:
            fig.update_yaxes(range=self.yrange)
        return fig

class PiePlot(DataPlot):
    def __init__(self, values:list|None = None, labels:list|None = None, max_visible:int|None=None, title:str|None=None):
        super().__init__(title)
        self.values = values
        self.labels = labels
        self.max_visible = max_visible

    def empty(self):
        return self.values is None

    def _build(self):
        hidden = self.labels[:-self.max_visible] if len(self.labels) > self.max_visible else None
        fig = go.Figure(go.Pie(labels=self.labels, values=self.values, hole=0.3, textinfo="none"))
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), hiddenlabels=hidden)
        return fig
