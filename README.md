## Nephele
Nephele is a Microbiome Cloud Pilot project developed and managed by the Bioinformatics and Computational Biosciences Branch ([BCBB](http://www.niaid.nih.gov/about/organization/odoffices/omo/ocicb/pages/bcbb.aspx)), which is part of the National Institute of Allergy and Infectious Diseases (NIAID).

Nephele intends to allow non-expert users to process microbiome datasets through a pipeline of existing software tools. Typically this type of work is computationally intensive, and also demands knowledge of both scripting and the tools themselves. Nephele attempts to address these issues.

To address the computationally intensive aspect, we provision dedicated, cloud-based compute resources, in an on-demand nature and with an appropriate environment for analyzing user-supplied data. When an analysis pipeline completes, this compute resource is torn down. This means users can process as many datasets as they choose, simultaneously, by machines that are dynamically spun up and shut down.

To ease the learning curve of installing, configuring, and running the software, we stitch together a series of computational tasks into a number of prepared generic pipelines. Pipelines are configured using inputs from simple web-front-end forms, which allow users to specify commonly-changed parameters. We combine these with sensible default parameters, when appropriate.

It is important to note that *all* of the software which comprises Nephele--for example [mothur](http://www.mothur.org/), [QIIME](http://qiime.org/), [bioBakery](https://bitbucket.org/biobakery/biobakery/wiki/Home), and [a5-miseq](https://sourceforge.net/projects/ngopt/)--is freely available for use. We do not attempt to supersede or act as a replacement for this software, nor do we modify it. Nephele instead attempts to take a number of useful tools and provide them to a wider audience. We recommend visiting the software creators' websites for details of their implementation. To examine how we use these tools, users can explore this repository as well as view log files that accompany each job and detail how each component of the pipeline was executed.

Nephele's pipelines have been collated from a number of sources, and all are being actively worked on.

Nephele currently uses Amazon's EC2 platform as a compute resource with curated machine images. We use Amazon's S3 service to store pipeline results for a period of time.

We would like to thank all contributors to this project, and are grateful for feedback.
