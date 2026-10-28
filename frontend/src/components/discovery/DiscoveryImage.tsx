import { useState } from 'react'

type Image = {
  kind: 'photo' | 'illustration' | 'original_placeholder'
  url: string | null
  attribution: string
  provenance: string
  permission_reference: string | null
  identity_reference: string | null
}

export default function DiscoveryImage({ image }: { image: Image }) {
  const [failed, setFailed] = useState(false)
  const available = image.kind !== 'original_placeholder' && image.url && !failed
  return <figure className="discovery-picture">
    {available ? <img src={image.url ?? undefined} alt={image.kind === 'photo' ? 'Photograph of the depicted watch' : 'Illustration of the depicted watch'}
      loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed(true)} /> :
      <p>Product image unavailable. Generic placeholder; does not depict this watch.</p>}
    <figcaption>{available ? image.kind === 'photo' ? 'Photograph' : 'Product illustration; not a photograph' : 'Placeholder'}
      <br />{image.attribution}<br />{image.provenance}
      {available && <details><summary>Image evidence</summary>
        <p>Permission: {image.permission_reference}</p><p>Depiction: {image.identity_reference}</p>
      </details>}
    </figcaption>
  </figure>
}
