"""Reusable image treatments inspired by editorial references; no raster edits."""
import html
import re

CLIPS = {
    'diagonal':'polygon(22% 0,100% 0,100% 100%,0 100%)',
    'brush':'polygon(30% 0,100% 0,100% 100%,0 100%,3% 93%,2% 91%,6% 85%,5% 82%,9% 76%,8% 73%,12% 66%,11% 63%,15% 56%,14% 54%,19% 45%,18% 42%,22% 34%,21% 31%,25% 23%,24% 20%,29% 10%,28% 7%)',
    'torn':'polygon(15% 0,100% 0,100% 100%,14% 100%,17% 92%,11% 86%,16% 78%,10% 72%,13% 65%,7% 59%,10% 52%,5% 46%,11% 39%,9% 33%,16% 25%,12% 18%,18% 11%)',
    'plain':'none',
    'clean_crop':'none',
    'rounded':'none',
}


def is_interface_asset(asset: dict) -> bool:
    """Protect actual interfaces even in older assets labelled as photographs."""
    label=str(asset.get('label',''))
    return (asset.get('image_kind') in {'logo','screenshot','promotional'} or
            bool(re.search(r'screenshot|screen|interface|giao diện|ứng dụng|mobile banking|màn hình|app\b|tcinvest-img',label,re.I)))


def photo_frame(asset: dict, treatment: str='diagonal') -> str:
    # The supplied PptxGenJS image demo makes the contain/cover/crop distinction
    # explicit. Product interfaces and logos must remain complete; photographs
    # can fill a frame, with a bounded focal point when one is supplied.
    screenshot = is_interface_asset(asset)
    clip = 'none' if screenshot else CLIPS.get(treatment,CLIPS['diagonal'])
    fit = 'contain' if screenshot or treatment=='plain' else 'cover'
    def focus(axis: str) -> int:
        try:
            value = float(asset.get(f'focus_{axis}', .5))
        except (TypeError, ValueError):
            value = .5
        return round(min(1., max(0., value)) * 100)

    rounded = treatment in {'rounded', 'clean_crop'}
    radius = '20px' if treatment=='rounded' else '12px'
    frame_style = (';overflow:hidden;border-radius:'+radius+
                   ';box-shadow:0 12px 28px rgba(17,31,40,.14)') if rounded else ''
    source = html.escape(str(asset['url']), quote=True)
    label = html.escape(str(asset.get('label', 'Ảnh minh họa')), quote=True)
    return (f'<figure data-image-treatment="{html.escape(treatment,quote=True)}" '
            f'style="margin:0;min-width:0;min-height:0;height:100%;background:transparent{frame_style}">'
            f'<img src="{source}" '
            f'alt="{label}" '
            f'style="display:block;width:100%;height:100%;object-fit:{fit};'
            f'object-position:{focus("x")}% {focus("y")}%;clip-path:{clip}"></figure>')
