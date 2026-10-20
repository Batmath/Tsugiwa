import plotly.express as px
import plotly.graph_objects as go


class DataPlot:
    def __init__(self, title:str|None = None):
        self.title = title

    def empty(self) -> bool:
        raise NotImplementedError

    def _build(self) -> go.Figure:
        raise NotImplementedError

    def figure(self) -> go.Figure:
        empty = self.empty()
        fig = go.Figure() if empty else self._build()
        fig = self._style(fig)
        if empty:
            fig.update_xaxes(visible=False)
            fig.update_yaxes(visible=False)
        return fig

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
        return (self.x is None or self.y is None or len(self.x) == 0 or len(self.y) == 0)

    def _build(self):
        hover = {f"{self.hover_name}": self.hover} if self.hover is not None else None
        fig = px.scatter(x=self.x, y=self.y, hover_data=hover, labels={"x": self.labelx, "y": self.labely})
        if self.xrange:
            fig.update_xaxes(range=self.xrange)
        if self.yrange:
            fig.update_yaxes(range=self.yrange)
        return fig

class PiePlot(DataPlot):
    def __init__(self, values:list|None = None, labels:list|None = None, max_visible:int|None=None, title:str|None=None, color_map:dict|None=None):
        super().__init__(title)
        self.values = values
        self.labels = labels
        self.max_visible = max_visible
        self.color_map = color_map

    def empty(self):
        return self.values is None or len(self.values) == 0

    def _build(self):
        hidden = self.labels[:-self.max_visible] if len(self.labels) > self.max_visible else None
        fig = go.Figure(go.Pie(labels=self.labels, values=self.values, hole=0.3, textinfo="none"))
        fig.update_layout(margin={"t": 20, "b": 20, "l": 20, "r": 20}, hiddenlabels=hidden)
        return fig

class HistoPlot(DataPlot):

    def __init__(self, x, nbins=10, title=None, xrange=(0.5, 10.5), color="#641791", xlabel="Score", ylabel="Count", show_mean=True, 
                 show_median=False, hovertemplate=None):
        super().__init__(title)
        self.x, self.nbins = x, nbins
        self.xrange, self.color = xrange, color
        self.xlabel, self.ylabel = xlabel, ylabel
        self.show_mean, self.show_median = show_mean, show_median
        self.hovertemplate = hovertemplate

    def empty(self):
        return self.x is None or len(self.x) == 0

    def _build(self):
        fig = go.Figure(go.Histogram(x=self.x, xbins={"start": self.xrange[0], "end": self.xrange[1], "size": 1},
                        marker={"color": self.color, "line": {"color": "rgba(255,255,255,0.35)", "width": 1}},
                        opacity=0.9, hovertemplate=self.hovertemplate))
        fig.update_layout(bargap=0.06, xaxis_title=self.xlabel, yaxis_title=self.ylabel, margin={"t": 40, "b": 40, "l": 40, "r": 20})
        fig.update_xaxes(range=self.xrange, dtick=1)
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)", zeroline=False)
        return fig

class ImagePlot(DataPlot):

    def __init__(self, width: int, height: int, scale_factor: float = 1.0, source=None, title: str | None = None):
        super().__init__(title)
        self.width, self.height = width, height
        self.scale_factor = scale_factor
        self.source = source

    def empty(self) -> bool:
        return self.source is None

    def _build(self) -> go.Figure:
        w = self.width * self.scale_factor
        h = self.height * self.scale_factor

        fig = go.Figure()

        fig.add_trace(go.Scatter(x=[0, w], y=[0, h], mode="markers", marker_opacity=0, hoverinfo="skip"))
        fig.update_xaxes(visible=False, range=[0, w])
        fig.update_yaxes(visible=False, range=[0, h], scaleanchor="x")
        fig.add_layout_image({"source": self.source, "x": 0, "y": h, "sizex": w, "sizey": h, "xref": "x", "yref": "y", "opacity": 1.0, "layer": "below", "sizing": "stretch"})
        fig.update_layout(width=w, height=h, margin={"l": 0, "r": 0, "t": 0, "b": 0})

        return fig
